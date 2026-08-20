"""Feature engineering shared by training (the notebook) and serving (the API).

The single most common way a forecasting system fails in production is
*training/serving skew*: the notebook computes a feature one way, the API
computes it another way, and the model silently receives inputs it was never
trained on.  The defence is to have exactly one implementation, imported by
both.  That is this module.

Everything here is horizon-safe for a 28-day-ahead forecast: no feature uses
information that would be unavailable 28 days before the target date.
Concretely, the only history features are ``lag_28`` and rolling windows built
with ``.shift(28)``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------
# Feature contract
# --------------------------------------------------------------------------

ID_FEATURES = ["item_code", "dept_code", "cat_code", "store_code", "state_code"]

CALENDAR_FEATURES = ["year", "month", "week", "day_of_week", "day_of_month",
                     "quarter", "day_of_year", "is_weekend"]

EVENT_FEATURES = ["snap", "is_event", "event_type_code", "is_christmas"]

PRICE_FEATURES = ["sell_price", "price_rel", "discount_pct", "price_change_7"]

HISTORY_FEATURES = ["lag_28", "rmean_7_h28", "rmean_28_h28", "rstd_28_h28"]

FEATURES = ID_FEATURES + CALENDAR_FEATURES + EVENT_FEATURES + PRICE_FEATURES + HISTORY_FEATURES

CATEGORICAL_FEATURES = ["item_code", "dept_code", "cat_code", "store_code",
                        "state_code", "event_type_code", "day_of_week", "month"]

SERIES_KEYS = ["item_id", "store_id"]

#: Days of history required before the first target day.
#: ``rmean_28_h28`` is ``shift(28).rolling(28)``, so it reaches 56 days back.
HISTORY_DAYS = 56

#: Forecast horizon the model was trained for.
HORIZON = 28

STATES = ["CA", "TX", "WI"]


# --------------------------------------------------------------------------
# Calendar
# --------------------------------------------------------------------------

def prepare_calendar(calendar: pd.DataFrame) -> pd.DataFrame:
    """Normalise ``calendar.csv`` into the columns the feature builder needs."""
    cal = calendar.copy()
    if "d_num" not in cal.columns:
        cal["d_num"] = cal["d"].str.slice(2).astype("int32")
    cal["date"] = pd.to_datetime(cal["date"])
    cal = cal.sort_values("d_num").reset_index(drop=True)

    cal["year"] = cal["date"].dt.year.astype("int16")
    cal["month"] = cal["date"].dt.month.astype("int8")
    cal["week"] = cal["date"].dt.isocalendar().week.astype("int8")
    cal["day_of_week"] = cal["date"].dt.dayofweek.astype("int8")     # 0 = Monday
    cal["day_of_month"] = cal["date"].dt.day.astype("int8")
    cal["quarter"] = cal["date"].dt.quarter.astype("int8")
    cal["day_of_year"] = cal["date"].dt.dayofyear.astype("int16")
    cal["is_weekend"] = cal["wday"].isin([1, 2]).astype("int8")      # wday 1 = Sat, 2 = Sun
    return cal


def event_type_categories(calendar: pd.DataFrame) -> list[str]:
    """Stable, sorted list of event-type labels; index in this list is the code."""
    return sorted(calendar["event_type_1"].dropna().unique().tolist() + ["NoEvent"])


# --------------------------------------------------------------------------
# Feature builder
# --------------------------------------------------------------------------

def build_features(
    panel: pd.DataFrame,
    calendar: pd.DataFrame,
    prices: pd.DataFrame,
    encoders: dict[str, dict[str, int]],
    event_types: list[str],
    price_max_seed: pd.Series | None = None,
) -> pd.DataFrame:
    """Attach every model feature to a (series x day) panel.

    Parameters
    ----------
    panel
        One row per (``item_id``, ``store_id``, ``d_num``) with columns
        ``dept_id``, ``cat_id``, ``state_id`` and ``sales``.  Rows whose sales
        are not yet known (the forecast horizon) carry ``NaN`` in ``sales``;
        they are still required as rows so their features can be built.
        Must cover at least ``HISTORY_DAYS`` observed days before the first
        target day.
    calendar
        Output of :func:`prepare_calendar`, covering every ``d_num`` in *panel*.
    prices
        ``sell_prices.csv`` restricted to the relevant items, with columns
        ``store_id``, ``item_id``, ``wm_yr_wk``, ``sell_price``.
    encoders
        ``{"item_id": {value: code}, ...}`` for each of the five id columns.
    event_types
        Output of :func:`event_type_categories`; position defines the code.
    price_max_seed
        Highest price seen for each series *before* this panel starts, indexed
        by (``item_id``, ``store_id``).  Keeps the expanding maximum continuous
        across a serving call that only carries recent history.  ``None`` seeds
        it at zero.

    Returns
    -------
    The panel with every column in :data:`FEATURES` added, sorted by series then
    day.  History features are ``NaN`` for the first :data:`HISTORY_DAYS` rows of
    each series; callers drop or ignore those.
    """
    df = panel.sort_values(SERIES_KEYS + ["d_num"], kind="stable").reset_index(drop=True)

    # ---- identity codes -------------------------------------------------
    for src, dst in [("item_id", "item_code"), ("dept_id", "dept_code"),
                     ("cat_id", "cat_code"), ("store_id", "store_code"),
                     ("state_id", "state_code")]:
        mapped = df[src].astype(str).map(encoders[src])
        if mapped.isna().any():
            unknown = sorted(df.loc[mapped.isna(), src].astype(str).unique())[:5]
            raise KeyError(f"unknown {src} value(s) for this model: {unknown}")
        df[dst] = mapped.astype("int16" if dst == "item_code" else "int8")

    # ---- calendar -------------------------------------------------------
    cal = calendar.set_index("d_num")
    take = df["d_num"].to_numpy()
    for col, dtype in [("year", "int16"), ("month", "int8"), ("week", "int8"),
                       ("day_of_week", "int8"), ("day_of_month", "int8"),
                       ("quarter", "int8"), ("day_of_year", "int16"),
                       ("is_weekend", "int8")]:
        df[col] = cal[col].reindex(take).to_numpy(dtype=dtype)
    df["wm_yr_wk"] = cal["wm_yr_wk"].reindex(take).to_numpy(dtype="int32")

    # ---- SNAP, resolved per state --------------------------------------
    snap_by_state = {s: cal[f"snap_{s}"].reindex(take).to_numpy(dtype="int8") for s in STATES}
    snap = np.zeros(len(df), dtype="int8")
    state_values = df["state_id"].astype(str).to_numpy()
    for s in STATES:
        snap = np.where(state_values == s, snap_by_state[s], snap)
    df["snap"] = snap

    # ---- events ---------------------------------------------------------
    name_1 = cal["event_name_1"].reindex(take)
    type_1 = cal["event_type_1"].reindex(take).fillna("NoEvent")
    code_of = {label: i for i, label in enumerate(event_types)}
    df["event_type_code"] = type_1.map(code_of).fillna(code_of["NoEvent"]).to_numpy(dtype="int8")
    df["is_event"] = name_1.notna().to_numpy(dtype="int8")
    df["is_christmas"] = (name_1 == "Christmas").fillna(False).to_numpy(dtype="int8")

    # ---- price ----------------------------------------------------------
    price_cols = ["store_id", "item_id", "wm_yr_wk", "sell_price"]
    p = prices[price_cols].copy()
    p["store_id"] = p["store_id"].astype(str)
    p["item_id"] = p["item_id"].astype(str)
    keys = df[["store_id", "item_id"]].astype(str)
    df = df.assign(_store=keys["store_id"], _item=keys["item_id"]).merge(
        p.rename(columns={"store_id": "_store", "item_id": "_item"}),
        on=["_store", "_item", "wm_yr_wk"], how="left").drop(columns=["_store", "_item"])
    df["sell_price"] = df["sell_price"].astype("float32")

    grp_price = df.groupby(SERIES_KEYS, observed=True)["sell_price"]

    # Expanding (not global) maximum: at day t this only ever sees prices up to
    # day t, so it carries no information from the future.
    running_max = grp_price.cummax()
    if price_max_seed is not None:
        seed = pd.MultiIndex.from_frame(df[SERIES_KEYS].astype(str))
        seeded = price_max_seed.reindex(seed).to_numpy(dtype="float64")
        running_max = np.fmax(running_max.to_numpy(dtype="float64"),
                              np.nan_to_num(seeded, nan=0.0))
        running_max = pd.Series(running_max, index=df.index)

    df["price_rel"] = (df["sell_price"] / running_max).astype("float32")
    df["discount_pct"] = ((1 - df["price_rel"]) * 100).astype("float32")
    df["price_change_7"] = ((df["sell_price"] / grp_price.shift(7) - 1) * 100
                            ).astype("float32").fillna(0)

    # ---- history: lag 28 and rolling windows ending 28 days back --------
    grp_sales = df.groupby(SERIES_KEYS, observed=True)["sales"]
    history = {
        "lag_28": grp_sales.shift(28),
        "rmean_7_h28": grp_sales.transform(lambda x: x.shift(28).rolling(7).mean()),
        "rmean_28_h28": grp_sales.transform(lambda x: x.shift(28).rolling(28).mean()),
        "rstd_28_h28": grp_sales.transform(lambda x: x.shift(28).rolling(28).std()),
    }
    df = df.assign(**{k: v.astype("float32") for k, v in history.items()})

    return df


def running_price_max(featured: pd.DataFrame) -> pd.Series:
    """Highest price seen per series, for seeding a later :func:`build_features` call."""
    return (featured.assign(**{k: featured[k].astype(str) for k in SERIES_KEYS})
                    .groupby(SERIES_KEYS, observed=True)["sell_price"].max())


def horizon_panel(
    history: pd.DataFrame,
    meta: pd.DataFrame,
    target_days: list[int],
) -> pd.DataFrame:
    """Stack observed history with empty rows for the days to be forecast.

    ``history`` holds the known ``sales``; the target rows are added with
    ``sales = NaN`` so :func:`build_features` can compute their features from
    the history without ever reading a future value.
    """
    cols = SERIES_KEYS + ["dept_id", "cat_id", "state_id", "d_num", "sales"]
    days = pd.DataFrame({"d_num": np.asarray(target_days, dtype="int32")})
    future = meta.merge(days, how="cross")
    future["sales"] = np.full(len(future), np.nan, dtype="float32")

    # Column-wise concatenation in NumPy. `pd.concat` would have to infer a dtype
    # for the all-NaN sales column and warns about it; this states every dtype.
    hist = history[cols]
    fut = future[cols]
    return pd.DataFrame({
        c: np.concatenate([hist[c].to_numpy(), fut[c].to_numpy()]) for c in cols
    })
