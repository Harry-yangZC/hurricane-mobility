"""Reusable plotting functions for mobility & hurricane analysis."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
from matplotlib.lines import Line2D


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _savefig(fig: plt.Figure, save_path: Path | str | None) -> None:
    if save_path is not None:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(str(save_path), dpi=300, bbox_inches="tight")
    plt.show()


def _anchor_to_year(
    dts: pd.DatetimeIndex, anchor_year: int = 2001
) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(
        [pd.Timestamp(anchor_year, dt.month, dt.day) for dt in dts]
    )


def _metric_title(metric: str) -> str:
    return (
        metric
        .replace("_percent_change_from_baseline", "")
        .replace("_", " ")
        .title()
    )


# ===================================================================
# Google Mobility plots (from NB02)
# ===================================================================

def plot_national_timeseries(
    df_national: pd.DataFrame,
    metrics: list[str],
    *,
    save_path: Path | str | None = None,
) -> None:
    """3x2 daily + 7-day rolling mean national timeseries."""
    sns.set_theme(style="whitegrid")
    fig, axes = plt.subplots(3, 2, figsize=(16, 12), sharex=True)
    axes = axes.flatten()
    for i, metric in enumerate(metrics):
        ax = axes[i]
        series = df_national.set_index("date")[metric].sort_index()
        ax.plot(series.index, series.values, color="lightgray", linewidth=0.8,
                label="Daily")
        ax.plot(series.rolling(7, min_periods=1).mean(), color="C0",
                linewidth=1.8, label="7d mean")
        ax.set_title(_metric_title(metric))
        ax.axhline(0, color="black", linewidth=0.8, alpha=0.5)
        ax.set_ylabel("% vs baseline")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=2)
    fig.autofmt_xdate()
    fig.tight_layout(rect=[0, 0.03, 1, 1])
    _savefig(fig, save_path)


def plot_state_small_multiples(
    df_state: pd.DataFrame,
    metrics: list[str],
    *,
    save_path_prefix: Path | str | None = None,
) -> None:
    """One figure per metric with 7-day rolling mean per state."""
    states = sorted(df_state["sub_region_1"].dropna().unique())
    num_states = len(states)
    cols = 6
    rows = int(np.ceil(num_states / cols))

    for metric in metrics:
        fig, axes = plt.subplots(rows, cols, figsize=(18, rows * 2.4),
                                 sharex=True, sharey=True)
        axes = axes.flatten()
        for idx, state in enumerate(states):
            ax = axes[idx]
            s = (
                df_state[df_state["sub_region_1"] == state]
                .set_index("date")[metric]
                .sort_index()
            )
            ax.plot(s.rolling(7, min_periods=1).mean(), color="C1",
                    linewidth=1.0)
            ax.set_title(state, fontsize=8)
            ax.axhline(0, color="black", linewidth=0.4, alpha=0.4)
        for j in range(num_states, len(axes)):
            axes[j].axis("off")
        fig.suptitle(_metric_title(metric))
        fig.tight_layout(rect=[0, 0.03, 1, 0.97])
        sp = (
            Path(f"{save_path_prefix}{_metric_title(metric).replace(' ', '_')}.png")
            if save_path_prefix else None
        )
        _savefig(fig, sp)


def plot_state_week_heatmaps(
    df_state: pd.DataFrame,
    metrics: list[str],
    regions: dict[str, list[str]],
    *,
    save_path: Path | str | None = None,
) -> None:
    """3x2 state-by-week heatmap for each metric."""
    weekly = (
        df_state.assign(
            week_start=lambda x: (
                x["date"]
                - pd.to_timedelta(x["date"].dt.weekday, unit="D")
            ).dt.normalize()
        )
        .groupby(["sub_region_1", "week_start"], observed=False)[metrics]
        .median()
        .reset_index()
    )

    present = set(weekly["sub_region_1"].unique())
    ordered: list[str] = []
    for grp in ("Northeast", "Midwest", "South", "West"):
        ordered.extend(s for s in regions.get(grp, []) if s in present)
    ordered.extend(sorted(present - set(ordered)))
    dates_weeks = pd.to_datetime(sorted(weekly["week_start"].unique()))

    nrows, ncols = 3, 2
    fig, axes = plt.subplots(nrows, ncols, figsize=(18, 12), sharey=True)
    axes = axes.flatten()

    for ax, metric in zip(axes, metrics):
        mat = weekly.pivot(
            index="sub_region_1", columns="week_start", values=metric
        )
        mat = mat.reindex(index=ordered, columns=dates_weeks).astype(float)
        vals = weekly[metric].astype(float).to_numpy()
        v = np.nanpercentile(np.abs(vals), 99)
        v = 5.0 if not np.isfinite(v) or v == 0 else v
        sns.heatmap(
            mat, ax=ax, cmap="coolwarm", center=0, vmin=-v, vmax=v,
            cbar=True, cbar_kws={"label": "% vs Jan-Feb 2020 baseline"},
        )
        ax.set_title(_metric_title(metric))
        ax.set_xlabel("Week start")
        ax.set_ylabel("State")
        col_dates = mat.columns.to_list()
        month_ticks = [0]
        for i in range(1, len(col_dates)):
            if col_dates[i - 1].month != col_dates[i].month:
                month_ticks.append(i)
        if month_ticks:
            step = max(1, int(np.ceil(len(month_ticks) / 24)))
            sel = month_ticks[::step]
            ax.set_xticks(sel)
            ax.set_xticklabels(
                [col_dates[i].strftime("%Y-%m") for i in sel],
                rotation=45, ha="right", fontsize=8,
            )
        ax.tick_params(axis="y", labelsize=8)

    for j in range(len(metrics), nrows * ncols):
        axes[j].axis("off")
    plt.tight_layout()
    _savefig(fig, save_path)


# ---------------------------------------------------------------------------
# Holiday helpers
# ---------------------------------------------------------------------------

def selected_holidays(
    years: tuple[int, ...] = (2020, 2021, 2022),
) -> list[tuple[pd.Timestamp, str]]:
    """Return a list of ``(date, label)`` for major US holidays."""
    labels: list[tuple[pd.Timestamp, str]] = []
    for y in years:
        labels.append((pd.Timestamp(y, 1, 1), "New Year"))
        last_may = pd.Timestamp(y, 5, 31)
        memorial = last_may - pd.to_timedelta(
            (last_may.weekday() - 0) % 7, unit="D"
        )
        labels.append((memorial, "Memorial Day"))
        labels.append((pd.Timestamp(y, 7, 4), "July 4"))
        sept1 = pd.Timestamp(y, 9, 1)
        labor = sept1 + pd.to_timedelta((0 - sept1.weekday()) % 7, unit="D")
        labels.append((labor, "Labor Day"))
        nov1 = pd.Timestamp(y, 11, 1)
        first_thu_offset = (3 - nov1.weekday()) % 7
        thanksgiving = nov1 + pd.to_timedelta(first_thu_offset + 21, unit="D")
        labels.append((thanksgiving, "Thanksgiving"))
        labels.append((pd.Timestamp(y, 12, 25), "Christmas"))
    return labels


def plot_national_timeseries_with_holidays(
    df_national: pd.DataFrame,
    metrics: list[str],
    holidays: list[tuple[pd.Timestamp, str]],
    *,
    save_path: Path | str | None = None,
) -> None:
    """National timeseries with vertical holiday markers."""
    min_d, max_d = df_national["date"].min(), df_national["date"].max()
    hols = [(d, lab) for d, lab in holidays if min_d <= d <= max_d]

    sns.set_theme(style="whitegrid")
    fig, axes = plt.subplots(3, 2, figsize=(16, 12), sharex=True)
    axes = axes.flatten()
    for i, metric in enumerate(metrics):
        ax = axes[i]
        series = df_national.set_index("date")[metric].sort_index()
        ax.plot(series.index, series.values, color="lightgray", linewidth=0.8,
                label="Daily")
        ax.plot(series.rolling(7, min_periods=1).mean(), color="C0",
                linewidth=1.8, label="7d mean")
        for d, lab in hols:
            ax.axvline(d, color="k", alpha=0.15, linewidth=0.8)
            ax.text(d, ax.get_ylim()[1], lab, rotation=90, va="top",
                    ha="right", fontsize=7, alpha=0.8)
        ax.set_title(_metric_title(metric))
        ax.axhline(0, color="black", linewidth=0.8, alpha=0.5)
        ax.set_ylabel("% vs baseline")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=2)
    fig.autofmt_xdate()
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    _savefig(fig, save_path)


# ---------------------------------------------------------------------------
# DOW profiles
# ---------------------------------------------------------------------------

def plot_national_dow_profiles(
    df_national: pd.DataFrame,
    metrics: list[str],
    *,
    save_path_prefix: Path | str | None = None,
) -> None:
    """Mean day-of-week profile by year for national rows."""
    nat = df_national.copy()
    nat["dow"] = nat["date"].dt.day_name()
    nat["year"] = nat["date"].dt.year
    dow_order = [
        "Monday", "Tuesday", "Wednesday", "Thursday",
        "Friday", "Saturday", "Sunday",
    ]
    profiles = (
        nat.groupby(["year", "dow"], observed=False)[metrics].mean().reset_index()
    )
    profiles["dow"] = pd.Categorical(
        profiles["dow"], categories=dow_order, ordered=True
    )
    profiles = profiles.sort_values(["year", "dow"])

    for metric in metrics:
        fig = plt.figure(figsize=(10, 4))
        sns.lineplot(data=profiles, x="dow", y=metric, hue="year", marker="o")
        plt.axhline(0, color="black", linewidth=0.8, alpha=0.5)
        plt.title(_metric_title(metric) + " \u2014 DOW profile")
        plt.ylabel("% vs baseline")
        plt.xlabel("Day of week")
        plt.legend(title="Year")
        plt.tight_layout()
        sp = (
            Path(f"{save_path_prefix}{_metric_title(metric).replace(' ', '_')}.png")
            if save_path_prefix else None
        )
        _savefig(fig, sp)


def plot_state_dow_profiles(
    df_state: pd.DataFrame,
    metrics: list[str],
    sel_states: list[str],
    *,
    save_path_prefix: Path | str | None = None,
) -> None:
    """State-level DOW profiles for selected states."""
    state_df = df_state[df_state["sub_region_1"].isin(sel_states)].copy()
    state_df["dow"] = state_df["date"].dt.day_name()
    state_df["year"] = state_df["date"].dt.year

    dow_order = [
        "Monday", "Tuesday", "Wednesday", "Thursday",
        "Friday", "Saturday", "Sunday",
    ]
    dow_abbrev = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    dow_to_abbr = dict(zip(dow_order, dow_abbrev))

    profiles = (
        state_df.groupby(["sub_region_1", "year", "dow"], observed=False)[metrics]
        .mean().reset_index()
    )
    profiles["dow"] = pd.Categorical(
        profiles["dow"], categories=dow_order, ordered=True
    )
    profiles["dow_abbr"] = profiles["dow"].map(
        lambda d: dow_to_abbr.get(str(d), str(d))
    )
    profiles["dow_abbr"] = pd.Categorical(
        profiles["dow_abbr"], categories=dow_abbrev, ordered=True
    )
    profiles = profiles.sort_values(["sub_region_1", "year", "dow_abbr"])

    ylim_by_metric: dict[str, tuple[float, float]] = {}
    for metric in metrics:
        vals = profiles[metric].to_numpy()
        low, high = np.nanpercentile(vals, [1, 99])
        m = max(abs(low), abs(high))
        ylim_by_metric[metric] = (-m, m)

    for metric in metrics:
        fig, axes = plt.subplots(
            1, len(sel_states), figsize=(16, 3.2), sharey=True
        )
        if len(sel_states) == 1:
            axes = [axes]
        for ax, st in zip(axes, sel_states):
            df_plot = profiles[profiles["sub_region_1"] == st]
            sns.lineplot(
                data=df_plot, x="dow_abbr", y=metric, hue="year",
                marker="o", ax=ax,
            )
            ax.axhline(0, color="black", linewidth=0.6, alpha=0.5)
            ax.set_title(st)
            ax.set_xlabel("")
            ax.set_ylim(ylim_by_metric[metric])
            ax.tick_params(axis="x", labelsize=8)
            if ax is axes[0]:
                ax.set_ylabel("% vs baseline")
            else:
                ax.set_ylabel("")
            if ax is not axes[-1]:
                leg = ax.get_legend()
                if leg is not None:
                    leg.remove()
            else:
                ax.legend(title="Year", bbox_to_anchor=(1.05, 1),
                          loc="upper left")
        plt.suptitle(_metric_title(metric) + " \u2014 State DOW profiles")
        plt.tight_layout()
        sp = (
            Path(f"{save_path_prefix}{_metric_title(metric).replace(' ', '_')}.png")
            if save_path_prefix else None
        )
        _savefig(fig, sp)


# ---------------------------------------------------------------------------
# Google mobility event-window plots
# ---------------------------------------------------------------------------

def plot_google_event_windows(
    df_national: pd.DataFrame,
    df_state: pd.DataFrame,
    events: list[dict],
    line_series: list[tuple[str, str | None]],
    metrics: list[str],
    *,
    save_path_prefix: Path | str | None = None,
) -> None:
    """Event-window plots: six metrics, multiple state lines per event."""
    palette = sns.color_palette("colorblind", n_colors=len(line_series))
    label_to_color = {lab: palette[i] for i, (lab, _) in enumerate(line_series)}

    def _get_series(
        state_name: str | None, metric: str, dt_index: pd.DatetimeIndex,
    ) -> pd.Series:
        if state_name is None:
            s = df_national.set_index("date")[metric]
        else:
            s = (
                df_state[df_state["sub_region_1"] == state_name]
                .set_index("date")[metric]
            )
        return s.sort_index().reindex(dt_index)

    for ev in events:
        start, end = ev["window_start"], ev["window_end"]
        landfall = ev["landfall"]
        landfall_state = ev["landfall_state"]
        ext_start = start - pd.Timedelta(days=14)
        ext_end = end + pd.Timedelta(days=14)
        idx = pd.date_range(ext_start, ext_end, freq="D")

        fig, axes = plt.subplots(3, 2, figsize=(16, 9), sharex=True)
        axes = axes.flatten()
        for i, metric in enumerate(metrics):
            ax = axes[i]
            for label, st in line_series:
                series = _get_series(st, metric, idx)
                if label == "National":
                    color, lw = "black", 2.8
                elif st == landfall_state:
                    color, lw = label_to_color[label], 2.4
                else:
                    color, lw = label_to_color[label], 1.6
                ax.plot(idx, series.values, label=label, color=color,
                        linewidth=lw)
            ax.axvspan(start, end, color="grey", alpha=0.15)
            ax.axvline(landfall, color="red", linestyle="--", linewidth=1.0,
                       alpha=0.8)
            ax.axhline(0, color="black", linewidth=0.6, alpha=0.5)
            ax.set_title(
                _metric_title(metric)
                + f" \u2014 Landfall: {landfall.strftime('%Y-%m-%d')}"
            )
            ax.set_ylabel("% vs baseline")

        handles, labels = axes[0].get_legend_handles_labels()
        lf_proxy = Line2D(
            [0], [0], color="red", linestyle="--", linewidth=1.0,
            label="Landfall date",
        )
        fig.legend(
            handles + [lf_proxy], labels + ["Landfall date"],
            loc="lower center", ncol=len(line_series) + 1,
        )
        fig.suptitle(
            f"{ev['name']} \u2014 {ext_start.date()} to {ext_end.date()} "
            "(shaded: Hurricane Window)"
        )
        fig.autofmt_xdate()
        fig.tight_layout(rect=(0, 0.05, 1, 0.97))
        sp = (
            Path(f"{save_path_prefix}{ev['name'].replace(' ', '_')}.png")
            if save_path_prefix else None
        )
        _savefig(fig, sp)


def plot_google_yoy_landfall(
    df_state: pd.DataFrame,
    events_with_state: list[dict],
    metrics: list[str],
    *,
    save_path_prefix: Path | str | None = None,
) -> None:
    """YoY overlays for landfall states (Google mobility data)."""
    for event in events_with_state:
        start = event["window_start"]
        end = event["window_end"]
        landfall = event["landfall"]
        landfall_state = event["landfall_state"]
        base_year = start.year
        years = [2020, 2021, 2022]
        start_md = start.strftime("%m-%d")
        end_md = end.strftime("%m-%d")
        landfall_md = landfall.strftime("%m-%d")

        year_to_idx: dict[int, pd.DatetimeIndex] = {}
        year_to_window: dict[int, tuple] = {}
        for y in years:
            try:
                s_y = pd.Timestamp(f"{y}-{start_md}")
                e_y = pd.Timestamp(f"{y}-{end_md}")
                idx = pd.date_range(
                    s_y - pd.Timedelta(days=14),
                    e_y + pd.Timedelta(days=14), freq="D",
                )
                year_to_idx[y] = idx
                year_to_window[y] = (s_y, e_y)
            except Exception:
                continue

        fig, axes = plt.subplots(3, 2, figsize=(16, 9), sharex=True)
        axes = axes.flatten()
        palette = sns.color_palette("colorblind", n_colors=len(year_to_idx))
        ytc = {y: palette[i] for i, y in enumerate(sorted(year_to_idx))}

        for i, metric in enumerate(metrics):
            ax = axes[i]
            for y in sorted(year_to_idx):
                idx = year_to_idx[y]
                series = (
                    df_state[df_state["sub_region_1"] == landfall_state]
                    .set_index("date")[metric]
                    .sort_index().reindex(idx)
                )
                anch = _anchor_to_year(idx, 2001)
                ax.plot(
                    anch, series.values, label=str(y), color=ytc[y],
                    linewidth=2.0 if y == base_year else 1.6,
                )
                ws, we = year_to_window[y]
                ax.axvspan(
                    pd.Timestamp(2001, ws.month, ws.day),
                    pd.Timestamp(2001, we.month, we.day),
                    color="grey", alpha=0.12,
                )
            lf_anch = pd.Timestamp(
                2001, int(landfall_md[:2]), int(landfall_md[3:])
            )
            ax.axvline(lf_anch, color="red", linestyle="--", linewidth=1.0,
                       alpha=0.8)
            ax.axhline(0, color="black", linewidth=0.6, alpha=0.5)
            ax.set_title(f"{_metric_title(metric)} \u2014 {landfall_state}")
            ax.set_xlabel("Date")
            ax.set_ylabel("% vs baseline")
            ax.xaxis.set_major_formatter(DateFormatter("%m-%d"))

        handles, labels = axes[0].get_legend_handles_labels()
        lf_proxy = Line2D(
            [0], [0], color="red", linestyle="--", linewidth=1.0,
            label="Landfall date",
        )
        fig.legend(
            handles + [lf_proxy], labels + ["Landfall date"],
            title="Year", loc="lower center",
            ncol=len(year_to_idx) + 1,
        )
        fig.suptitle(
            f"{event['name']} \u2014 {landfall_state}: "
            f"{start_md}\u2013{end_md} (shaded: Hurricane Window)"
        )
        fig.tight_layout(rect=(0, 0.05, 1, 0.97))
        sp = (
            Path(
                f"{save_path_prefix}"
                f"{event['name'].replace(' ', '_').replace(',', '')}.png"
            )
            if save_path_prefix else None
        )
        _savefig(fig, sp)


# ===================================================================
# BTS mobility event plots (from NB04)
# ===================================================================

def plot_bts_event_windows(
    bts: pd.DataFrame,
    events: list[dict],
    bts_metrics: list[str],
    *,
    save_path_prefix: Path | str | None = None,
) -> None:
    """+/-14 day BTS event-window plots with shaded landfall."""
    for ev in events:
        lf = ev["landfall_date"]
        st = ev["state_code"]
        ext_start = lf - pd.Timedelta(days=14)
        ext_end = lf + pd.Timedelta(days=14)
        idx = pd.date_range(ext_start, ext_end, freq="D")

        df = (
            bts[(bts["state_code"] == st) & bts["date"].between(ext_start, ext_end)]
            .set_index("date").reindex(idx)
        )
        fig, axes = plt.subplots(3, 2, figsize=(16, 9), sharex=True)
        axes = axes.flatten()

        for i, metric in enumerate(bts_metrics):
            ax = axes[i]
            ax.plot(df.index, df[metric].values, color="C0", linewidth=2.0,
                    label=st)
            ax.axvspan(
                lf - pd.Timedelta(days=3), lf + pd.Timedelta(days=3),
                color="grey", alpha=0.15,
            )
            ax.axvline(lf, color="red", linestyle="--", linewidth=1.0,
                       alpha=0.9)
            ax.set_title(metric)
            if metric.endswith("share"):
                ax.set_ylabel("share")
            elif metric == "Number of Trips":
                ax.set_ylabel("count")
            elif metric.startswith("Population "):
                ax.set_ylabel("people")
            else:
                ax.set_ylabel("value")

        lf_proxy = Line2D(
            [0], [0], color="red", linestyle="--", linewidth=1.0,
            label="Landfall date",
        )
        fig.legend([lf_proxy], ["Landfall date"], loc="lower center", ncol=1)
        fig.suptitle(
            f"{ev['name']} \u2014 {st}: {ext_start.date()} to {ext_end.date()} "
            "(shaded: \u00b13 days around landfall)"
        )
        fig.autofmt_xdate()
        fig.tight_layout(rect=(0, 0.05, 1, 0.97))
        sp = (
            Path(f"{save_path_prefix}{ev['name'].replace(' ', '_')}.png")
            if save_path_prefix else None
        )
        _savefig(fig, sp)


def plot_bts_yoy_all_states(
    bts: pd.DataFrame,
    hur: pd.DataFrame,
    bts_metrics: list[str],
    yoy_years: list[int],
    *,
    save_path_prefix: Path | str | None = None,
) -> None:
    """YoY overlays for every hurricane-state pair in the catalogue."""
    hur_events = hur.dropna(subset=["state_code", "landfall_date"]).copy()

    def _year(row: pd.Series) -> int | None:
        y = row.get("year")
        if pd.notna(y):
            try:
                return int(y)
            except Exception:
                pass
        lf = row.get("landfall_date")
        return pd.to_datetime(lf).year if pd.notna(lf) else None

    hur_events = hur_events[
        hur_events.apply(lambda r: _year(r) != 2024, axis=1)
    ]
    available = sorted(bts["date"].dt.year.unique().tolist())
    years_use = [y for y in yoy_years if y in available]

    for _, row in hur_events.iterrows():
        st = str(row["state_code"])
        lf = pd.to_datetime(row["landfall_date"])
        hy = _year(row) or lf.year
        name = f"{row['storm_name']} ({st}, {hy})"
        start = lf - pd.Timedelta(days=14)
        end = lf + pd.Timedelta(days=14)
        s_md, e_md, lf_md = (
            start.strftime("%m-%d"), end.strftime("%m-%d"),
            lf.strftime("%m-%d"),
        )

        series_by_year: dict[int, pd.DataFrame] = {}
        for y in years_use:
            idx = pd.date_range(
                pd.Timestamp(f"{y}-{s_md}"), pd.Timestamp(f"{y}-{e_md}"),
                freq="D",
            )
            sub = bts[
                (bts["state_code"] == st)
                & (bts["date"] >= idx[0])
                & (bts["date"] <= idx[-1])
            ]
            if sub.empty:
                continue
            series_by_year[y] = sub.set_index("date").reindex(idx)

        if not series_by_year:
            continue

        fig, axes = plt.subplots(3, 2, figsize=(16, 9), sharex=True)
        axes = axes.flatten()
        palette = sns.color_palette("colorblind", n_colors=len(series_by_year))
        ytc = {y: palette[i] for i, y in enumerate(sorted(series_by_year))}

        for i, metric in enumerate(bts_metrics):
            ax = axes[i]
            for y in sorted(series_by_year):
                idx = series_by_year[y].index
                anch = pd.DatetimeIndex(
                    [pd.Timestamp(2001, d.month, d.day) for d in idx]
                )
                lw = 3.0 if y == hy else 1.6
                ax.plot(
                    anch, series_by_year[y][metric].values,
                    color=ytc[y], linewidth=lw, label=str(y),
                    zorder=3 if y == hy else 2,
                )
            ax.axvspan(
                pd.Timestamp(2001, int(s_md[:2]), int(s_md[3:])),
                pd.Timestamp(2001, int(e_md[:2]), int(e_md[3:])),
                color="grey", alpha=0.12,
            )
            ax.axvline(
                pd.Timestamp(2001, int(lf_md[:2]), int(lf_md[3:])),
                color="red", linestyle="--", linewidth=1.0, alpha=0.9,
            )
            ax.xaxis.set_major_formatter(DateFormatter("%m-%d"))
            ax.set_title(metric)
            ax.set_ylabel("value")

        lf_proxy = Line2D(
            [0], [0], color="red", linestyle="--", linewidth=1.0,
            label="Landfall date",
        )
        handles, labels = axes[0].get_legend_handles_labels()
        fig.legend(
            handles + [lf_proxy], labels + ["Landfall date"],
            title="Year", loc="lower center",
            ncol=len(series_by_year) + 1,
        )
        fig.suptitle(
            f"{name} \u2014 {st}: {s_md}\u2013{e_md} "
            "(shaded: event window, bold = hurricane year)"
        )
        fig.tight_layout(rect=(0, 0.05, 1, 0.97))
        sp = (
            Path(f"{save_path_prefix}{name.replace(' ', '_').replace(',', '')}.png")
            if save_path_prefix else None
        )
        _savefig(fig, sp)


def plot_baseline_comparison(
    bts: pd.DataFrame,
    hur: pd.DataFrame,
    events_selected: list[dict],
    *,
    yoy_years: list[int] | None = None,
    save_path_prefix: Path | str | None = None,
) -> None:
    """Compare hurricane-year metrics vs. YoY baseline for each event."""
    from .features import compute_baseline_series

    yoy_years = yoy_years or [2019, 2020, 2021, 2022, 2023]
    share_compare = ["stay_home_share", "not_stay_home_share"]
    band_ratio = [
        "short_trips_per_1000", "medium_trips_per_1000", "long_trips_per_1000",
    ]
    plot_metrics = [
        "trips_per_1000", "stay_home_share", "not_stay_home_share",
        "short_trips_per_1000", "medium_trips_per_1000", "long_trips_per_1000",
    ]

    for ev in events_selected:
        st = ev["state_code"]
        lf = ev["landfall"]
        start = lf - pd.Timedelta(days=14)
        end = lf + pd.Timedelta(days=14)
        s_md = start.strftime("%m-%d")
        e_md = end.strftime("%m-%d")
        lf_md = lf.strftime("%m-%d")
        st_year = int(lf.year)

        idx_h = pd.date_range(start, end, freq="D")
        st_df = (
            bts[(bts["state_code"] == st)
                & (bts["date"] >= idx_h[0])
                & (bts["date"] <= idx_h[-1])]
            .set_index("date").reindex(idx_h)
        )
        anch_h = _anchor_to_year(st_df.index, 2001)
        baseline_map = compute_baseline_series(
            bts, hur, st, s_md, e_md, st_year, yoy_years,
            share_metrics=share_compare, band_ratio_metrics=band_ratio,
        )

        fig, axes = plt.subplots(3, 2, figsize=(16, 10), sharex=True)
        axes = axes.flatten()
        for i, m in enumerate(plot_metrics):
            ax = axes[i]
            if m in band_ratio:
                den = st_df["trips_per_1000"]
                with np.errstate(divide="ignore", invalid="ignore"):
                    h_vals = (st_df[m] / den).replace(
                        [np.inf, -np.inf], np.nan
                    )
                ax.plot(anch_h, h_vals.values, color="C0", linewidth=2.2,
                        label="Hurricane year")
            elif m in share_compare:
                ax.plot(anch_h, st_df[m].values, color="C0", linewidth=2.2,
                        label="Hurricane year")
            else:
                ax.plot(anch_h, st_df[m].values, color="C0", linewidth=2.2,
                        label="Hurricane year")

            base = baseline_map.get(m)
            if base is not None:
                ax.plot(base.index, base.values, color="C1", linewidth=2.0,
                        label="Baseline (mean other years)")

            ax.axvspan(
                pd.Timestamp(2001, int(s_md[:2]), int(s_md[3:])),
                pd.Timestamp(2001, int(e_md[:2]), int(e_md[3:])),
                color="grey", alpha=0.12,
            )
            ax.axvline(
                pd.Timestamp(2001, int(lf_md[:2]), int(lf_md[3:])),
                color="red", linestyle="--", linewidth=1.0, alpha=0.9,
            )
            ax.set_title(m)

        handles, labels = axes[0].get_legend_handles_labels()
        fig.legend(handles, labels, loc="lower center", ncol=2)
        fig.suptitle(
            f"{ev['name']} \u2014 {st}: Baseline vs Hurricane-year "
            "(shaded: event window)"
        )
        fig.autofmt_xdate()
        fig.tight_layout(rect=(0, 0.08, 1, 0.98))
        sp = (
            Path(f"{save_path_prefix}{ev['name'].replace(' ', '_')}.png")
            if save_path_prefix else None
        )
        _savefig(fig, sp)


def plot_percapita_yoy_overlays(
    bts: pd.DataFrame,
    events_selected: list[dict],
    selected_metrics: list[str],
    yoy_years: list[int],
    *,
    save_path_prefix: Path | str | None = None,
) -> None:
    """Per-capita YoY overlays with bold hurricane year."""
    band_ratio_set = {
        "short_trips_per_1000", "medium_trips_per_1000", "long_trips_per_1000",
    }
    for ev in events_selected:
        st = ev["state_code"]
        lf = ev["landfall"]
        start = lf - pd.Timedelta(days=14)
        end = lf + pd.Timedelta(days=14)
        s_md, e_md, lf_md = (
            start.strftime("%m-%d"), end.strftime("%m-%d"),
            lf.strftime("%m-%d"),
        )

        series_by_year: dict[int, pd.DataFrame] = {}
        for y in yoy_years:
            idx = pd.date_range(
                pd.Timestamp(f"{y}-{s_md}"), pd.Timestamp(f"{y}-{e_md}"),
                freq="D",
            )
            sub = bts[
                (bts["state_code"] == st)
                & (bts["date"] >= idx[0])
                & (bts["date"] <= idx[-1])
            ]
            if sub.empty:
                continue
            series_by_year[y] = sub.set_index("date").reindex(idx)
        if not series_by_year:
            continue

        fig, axes = plt.subplots(3, 2, figsize=(16, 9), sharex=True)
        axes = axes.flatten()
        cmap = plt.get_cmap("tab10")
        ordered = sorted(series_by_year)
        ytc = {y: cmap(i % 10) for i, y in enumerate(ordered)}

        for i, m in enumerate(selected_metrics):
            ax = axes[i]
            for y in ordered:
                idx = series_by_year[y].index
                anch = _anchor_to_year(idx, 2001)
                lw = 3.0 if y == int(lf.year) else 1.8
                if m in band_ratio_set:
                    den = series_by_year[y]["trips_per_1000"]
                    with np.errstate(divide="ignore", invalid="ignore"):
                        val = (
                            series_by_year[y][m] / den
                        ).replace([np.inf, -np.inf], np.nan)
                else:
                    val = series_by_year[y][m]
                ax.plot(anch, val.values, color=ytc[y], linewidth=lw,
                        label=str(y))
            ax.axvspan(
                pd.Timestamp(2001, int(s_md[:2]), int(s_md[3:])),
                pd.Timestamp(2001, int(e_md[:2]), int(e_md[3:])),
                color="grey", alpha=0.12,
            )
            ax.axvline(
                pd.Timestamp(2001, int(lf_md[:2]), int(lf_md[3:])),
                color="red", linestyle="--", linewidth=1.0, alpha=0.9,
            )
            if m in band_ratio_set or m.endswith("_share"):
                ax.set_ylabel("share")
            else:
                ax.set_ylabel("per 1,000")
            ax.set_title(m)

        handles, labels = axes[0].get_legend_handles_labels()
        lf_proxy = Line2D(
            [0], [0], color="red", linestyle="--", linewidth=1.0,
            label="Landfall date",
        )
        fig.legend(
            handles + [lf_proxy], labels + ["Landfall date"],
            loc="lower center", ncol=min(len(ordered) + 1, 6),
        )
        fig.suptitle(
            f"{ev['name']} \u2014 {st}: {start.date()} to {end.date()} "
            "(shaded: event window, bold = hurricane year)"
        )
        fig.autofmt_xdate()
        fig.tight_layout(rect=(0, 0.08, 1, 0.98))
        sp = (
            Path(f"{save_path_prefix}{ev['name'].replace(' ', '_')}.png")
            if save_path_prefix else None
        )
        _savefig(fig, sp)


def plot_seasonal_yoy_overlays(
    bts: pd.DataFrame,
    hur: pd.DataFrame,
    events_selected: list[dict],
    season_metrics: list[str],
    years: list[int],
    *,
    save_path_prefix: Path | str | None = None,
) -> None:
    """Full-year seasonal overlays with landfall markers."""
    sel_states = sorted({ev["state_code"] for ev in events_selected})
    band_ratio = {
        "short_trips_per_1000", "medium_trips_per_1000", "long_trips_per_1000",
    }

    hur_usable = hur.dropna(subset=["state_code", "landfall_date"]).copy()
    hur_usable["year"] = pd.to_datetime(
        hur_usable["landfall_date"], errors="coerce"
    ).apply(
        lambda d: int(pd.Timestamp(d).year) if pd.notna(d) else np.nan
    )
    st_hurr_yrs = {
        st: sorted(
            hur_usable.loc[hur_usable["state_code"] == st, "year"]
            .unique().tolist()
        )
        for st in sel_states
    }
    st_yr_lf: dict[tuple[str, int], list[pd.Timestamp]] = {}
    for st in sel_states:
        rows = hur_usable[hur_usable["state_code"] == st]
        for _, r in rows.iterrows():
            lf_ts = pd.Timestamp(r["landfall_date"])
            y = int(lf_ts.year)
            st_yr_lf.setdefault((st, y), []).append(lf_ts)

    for st in sel_states:
        print(f"Seasonal overlays for state {st}")
        fig, axes = plt.subplots(1, len(season_metrics),
                                 figsize=(9 * len(season_metrics), 6),
                                 sharex=True)
        if len(season_metrics) == 1:
            axes = [axes]
        else:
            axes = list(axes.flatten())

        for i, m in enumerate(season_metrics):
            ax = axes[i]
            ordered_years = [y for y in years if y in bts["year"].unique()]
            cmap = plt.get_cmap("tab10")
            year_to_series: dict[int, pd.Series] = {}
            full_anch = pd.date_range("2000-01-01", "2000-12-31", freq="D")
            for j, y in enumerate(ordered_years):
                mask = (bts["state_code"] == st) & (bts["year"] == y)
                needed = list(dict.fromkeys(["date", m, "trips_per_1000"]))
                sub = bts.loc[mask, needed].dropna()
                if sub.empty:
                    continue
                idx = pd.date_range(f"{y}-01-01", f"{y}-12-31", freq="D")
                sub = sub.set_index("date").reindex(idx)
                anch = pd.DatetimeIndex(
                    [pd.Timestamp(2000, d.month, d.day) for d in sub.index]
                )
                if m in band_ratio:
                    with np.errstate(divide="ignore", invalid="ignore"):
                        vals = (
                            sub[m].astype("float64")
                            / sub["trips_per_1000"].astype("float64")
                        ).replace([np.inf, -np.inf], np.nan)
                else:
                    vals = sub[m]
                s = pd.Series(vals.values, index=anch)
                s_smooth = s.rolling(7, min_periods=1, center=True).median()
                year_to_series[y] = s_smooth.reindex(full_anch)
                lw = 3.0 if y in st_hurr_yrs.get(st, []) else 1.6
                alpha = 1.0 if y in st_hurr_yrs.get(st, []) else 0.4
                ax.plot(s_smooth.index, s_smooth.values, color=cmap(j % 10),
                        linewidth=lw, alpha=alpha, label=str(y))

            non_hurr = [
                yy for yy in ordered_years
                if yy not in st_hurr_yrs.get(st, [])
            ]
            if non_hurr:
                df_ribbon = pd.concat(
                    [year_to_series[yy] for yy in non_hurr
                     if yy in year_to_series],
                    axis=1,
                )
                if df_ribbon is not None and not df_ribbon.empty:
                    q25 = df_ribbon.quantile(0.25, axis=1)
                    q75 = df_ribbon.quantile(0.75, axis=1)
                    q50 = df_ribbon.quantile(0.50, axis=1)
                    ax.fill_between(
                        df_ribbon.index, q25.values, q75.values,
                        color="grey", alpha=0.15, zorder=0,
                    )
                    ax.plot(
                        df_ribbon.index, q50.values,
                        color="grey", linestyle="--", linewidth=1.2,
                        alpha=0.7,
                    )

            for y in st_hurr_yrs.get(st, []):
                for lf in st_yr_lf.get((st, y), []):
                    lf_anch = pd.Timestamp(2000, lf.month, lf.day)
                    ax.axvline(lf_anch, color="red", linestyle="--",
                               linewidth=0.8, alpha=0.7)
            ax.set_title(m)

        handles, labels = axes[0].get_legend_handles_labels()
        fig.legend(
            handles, labels, title="Year", loc="lower center",
            ncol=min(len(ordered_years), 6),
        )
        fig.suptitle(
            f"Seasonal YoY overlays \u2014 {st} "
            f"({years[0]}\u2013{years[-1]}), bold = hurricane years; "
            "red dashed = landfalls"
        )
        fig.autofmt_xdate()
        fig.tight_layout(rect=(0, 0.08, 1, 0.98))
        sp = (
            Path(f"{save_path_prefix}{st}.png")
            if save_path_prefix else None
        )
        _savefig(fig, sp)
