"""FraudShield AI - Exploratory Data Analysis & Visualisation Engine.

Generates professional publication-grade visualisations using Matplotlib & Seaborn:
1. Transaction amount distribution (histogram + KDE with log-scale comparison).
2. Fraud vs. legitimate class distribution.
3. Payment channel / transaction type breakdown with fraud ratios.
4. Transaction frequency & velocity distribution.
5. Numerical feature correlation heatmap.
6. Diurnal time-based transaction patterns across 24 hours.
7. Outlier analysis via box plots and interquartile range bounds.

All charts use authentic dataset figures and are styled with FraudShield AI's
fintech cybersecurity palette (deep navy, electric blue, purple, crimson alert).
"""

from pathlib import Path
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for headless terminal execution
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd

from dataset.loader import DatasetLoader

# Styling constants
THEME_BG = "#0d131f"
THEME_CARD = "#161f30"
THEME_TEXT = "#f8fafc"
THEME_MUTED = "#94a3b8"
COLOR_BLUE = "#3b82f6"
COLOR_PURPLE = "#8b5cf6"
COLOR_CYAN = "#06b6d4"
COLOR_RED = "#ef4444"
COLOR_GREEN = "#10b981"
COLOR_AMBER = "#f59e0b"


class EDAVisualizer:
    """Generates and persists professional analytical charts for the dataset."""

    def __init__(
        self,
        dataset_path: str | Path = "dataset/raw/upi_transactions.csv",
        output_dir: str | Path = "documentation/figures",
    ) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        loader = DatasetLoader()
        self.df, self.summary = loader.load_dataset(file_path=dataset_path)

        # Set consistent global aesthetic
        sns.set_theme(style="darkgrid", font="sans-serif")
        plt.rcParams.update({
            "figure.facecolor": THEME_BG,
            "axes.facecolor": THEME_CARD,
            "axes.edgecolor": "#243046",
            "axes.labelcolor": THEME_TEXT,
            "xtick.color": THEME_MUTED,
            "ytick.color": THEME_MUTED,
            "text.color": THEME_TEXT,
            "grid.color": "#1e293b",
            "grid.alpha": 0.6,
            "font.size": 10,
        })

    def generate_all_visualisations(self) -> list[Path]:
        """Generates all 7 required analytical figures and returns saved paths."""
        saved_files = []
        saved_files.append(self.plot_amount_distribution())
        saved_files.append(self.plot_fraud_vs_legit_distribution())
        saved_files.append(self.plot_transaction_type_distribution())
        saved_files.append(self.plot_frequency_analysis())
        saved_files.append(self.plot_correlation_heatmap())
        saved_files.append(self.plot_time_based_patterns())
        saved_files.append(self.plot_outlier_analysis())
        saved_files.append(self.plot_summary_dashboard())
        return saved_files

    def plot_amount_distribution(self) -> Path:
        """Chart 1: Transaction Amount Distribution (Linear & Log Scales)."""
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        amt = self.df["amount"].dropna()

        # Subplot 1: Linear scale focusing on typical retail region (< ₹20,000)
        sns.histplot(
            amt[amt <= 20000],
            bins=40,
            kde=True,
            color=COLOR_CYAN,
            ax=axes[0],
            edgecolor=THEME_BG,
        )
        axes[0].set_title("Amount Distribution (Retail Region: ≤ ₹20,000)", fontsize=12, fontweight="bold", pad=10)
        axes[0].set_xlabel("Transaction Amount (INR)")
        axes[0].set_ylabel("Transaction Count")
        median_val = float(amt.median())
        axes[0].axvline(median_val, color=COLOR_AMBER, linestyle="--", linewidth=1.8, label=f"Median: ₹{median_val:,.0f}")
        axes[0].legend(facecolor=THEME_CARD, edgecolor="#243046")

        # Subplot 2: Log scale amount by ground-truth fraud label
        if "is_fraud" in self.df.columns:
            sns.kdeplot(
                data=self.df,
                x="amount",
                hue="is_fraud",
                common_norm=False,
                palette={0: COLOR_GREEN, 1: COLOR_RED},
                log_scale=True,
                fill=True,
                alpha=0.35,
                ax=axes[1],
            )
            axes[1].set_title("Density by Ground-Truth (Log Amount Scale)", fontsize=12, fontweight="bold", pad=10)
            axes[1].set_xlabel("Amount in INR (Logarithmic Scale)")
            axes[1].set_ylabel("Kernel Density")
            # Legend handled automatically by seaborn via hue

        plt.suptitle("FraudShield AI — Transaction Amount Distribution", fontsize=14, fontweight="bold", y=1.02)
        plt.tight_layout()
        dest = self.output_dir / "01_amount_distribution.png"
        fig.savefig(dest, dpi=300, bbox_inches="tight")
        plt.close(fig)
        return dest

    def plot_fraud_vs_legit_distribution(self) -> Path:
        """Chart 2: Fraud versus Legitimate Distribution."""
        fig, ax = plt.subplots(figsize=(8, 6))

        if "is_fraud" in self.df.columns:
            counts = self.df["is_fraud"].value_counts().sort_index()
            labels = ["Legitimate (0)", "Fraudulent (1)"]
            colors = [COLOR_GREEN, COLOR_RED]
            total = len(self.df)

            bars = ax.bar(labels, counts.values, color=colors, width=0.45, edgecolor=THEME_BG, linewidth=1.5)
            ax.set_title("Class Imbalance: Legitimate vs. Fraudulent Transactions", fontsize=13, fontweight="bold", pad=12)
            ax.set_ylabel("Number of Transactions")

            # Add count and percentage labels above bars
            for bar, count in zip(bars, counts.values):
                pct = (count / total) * 100
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + (total * 0.015),
                    f"{count:,}\n({pct:.2f}%)",
                    ha="center",
                    va="bottom",
                    fontsize=11,
                    fontweight="bold",
                    color=THEME_TEXT,
                )

            ax.set_ylim(0, max(counts.values) * 1.15)
        else:
            ax.text(0.5, 0.5, "No Ground Truth 'is_fraud' column present", ha="center", va="center")

        plt.tight_layout()
        dest = self.output_dir / "02_fraud_vs_legit_distribution.png"
        fig.savefig(dest, dpi=300, bbox_inches="tight")
        plt.close(fig)
        return dest

    def plot_transaction_type_distribution(self) -> Path:
        """Chart 3: Transaction Type / Payment Channel Breakdown."""
        fig, axes = plt.subplots(1, 2, figsize=(15, 6))
        ch_col = "channel" if "channel" in self.df.columns else "type"

        # Volume by channel
        channel_counts = self.df[ch_col].value_counts()
        colors = [COLOR_BLUE, COLOR_PURPLE, COLOR_CYAN, COLOR_AMBER]
        channel_counts.plot(
            kind="bar",
            ax=axes[0],
            color=colors[:len(channel_counts)],
            edgecolor=THEME_BG,
        )
        axes[0].set_title("Transaction Volume by Payment Channel", fontsize=12, fontweight="bold", pad=10)
        axes[0].set_xlabel("Payment Channel")
        axes[0].set_ylabel("Transaction Count")
        axes[0].tick_params(axis="x", rotation=15)

        # Fraud rate by channel
        if "is_fraud" in self.df.columns:
            fraud_rates = self.df.groupby(ch_col)["is_fraud"].mean() * 100
            fraud_rates = fraud_rates.reindex(channel_counts.index)
            bars = axes[1].bar(
                fraud_rates.index,
                fraud_rates.values,
                color=COLOR_RED,
                alpha=0.85,
                edgecolor=THEME_BG,
            )
            axes[1].set_title("Fraud Incident Rate by Channel (%)", fontsize=12, fontweight="bold", pad=10)
            axes[1].set_xlabel("Payment Channel")
            axes[1].set_ylabel("Fraud Percentage (%)")
            axes[1].tick_params(axis="x", rotation=15)

            for bar in bars:
                h = bar.get_height()
                axes[1].text(
                    bar.get_x() + bar.get_width() / 2,
                    h + 0.3,
                    f"{h:.2f}%",
                    ha="center",
                    va="bottom",
                    fontweight="bold",
                    fontsize=10,
                )
            axes[1].set_ylim(0, max(fraud_rates.values) * 1.25)

        plt.suptitle("FraudShield AI — Payment Channel Analysis", fontsize=14, fontweight="bold", y=1.02)
        plt.tight_layout()
        dest = self.output_dir / "03_transaction_type_distribution.png"
        fig.savefig(dest, dpi=300, bbox_inches="tight")
        plt.close(fig)
        return dest

    def plot_frequency_analysis(self) -> Path:
        """Chart 4: Transaction Frequency / Velocity Analysis."""
        fig, ax = plt.subplots(figsize=(10, 5))

        vel_col = "velocity_15m" if "velocity_15m" in self.df.columns else None
        if vel_col and "is_fraud" in self.df.columns:
            # Grouped bar chart comparing velocity distribution for normal vs fraud
            cross_tab = pd.crosstab(self.df[vel_col], self.df["is_fraud"], normalize="columns") * 100
            cross_tab.plot(
                kind="bar",
                ax=ax,
                color=[COLOR_GREEN, COLOR_RED],
                edgecolor=THEME_BG,
                width=0.75,
            )
            ax.set_title("15-Minute Transaction Velocity: Normal vs. Fraudulent (%)", fontsize=13, fontweight="bold", pad=12)
            ax.set_xlabel("Transaction Velocity (Count in Trailing 15 Minutes)")
            ax.set_ylabel("Percentage within Class (%)")
            ax.legend(["Legitimate (0)", "Fraudulent (1)"], facecolor=THEME_CARD, edgecolor="#243046")
            ax.tick_params(axis="x", rotation=0)
        else:
            ax.text(0.5, 0.5, "Velocity data not present", ha="center", va="center")

        plt.tight_layout()
        dest = self.output_dir / "04_transaction_frequency_analysis.png"
        fig.savefig(dest, dpi=300, bbox_inches="tight")
        plt.close(fig)
        return dest

    def plot_correlation_heatmap(self) -> Path:
        """Chart 5: Correlation Heatmap for Numerical Features."""
        fig, ax = plt.subplots(figsize=(10, 8))

        # Select continuous and binary numerical features
        numeric_candidates = [
            "amount", "velocity_15m", "is_new_device", "user_avg_amount", "is_fraud"
        ]
        available_cols = [c for c in numeric_candidates if c in self.df.columns]

        # Add derived hour if timestamp is available
        df_corr = self.df[available_cols].copy()
        if "timestamp" in self.df.columns:
            try:
                df_corr["hour"] = pd.to_datetime(self.df["timestamp"], utc=True).dt.hour
                df_corr["is_midnight"] = df_corr["hour"].apply(lambda h: 1 if h in [1, 2, 3, 4] else 0)
            except Exception:
                pass

        corr_matrix = df_corr.corr(method="spearman")

        mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
        sns.heatmap(
            corr_matrix,
            mask=mask,
            annot=True,
            fmt=".2f",
            cmap="mako",
            vmin=-0.4,
            vmax=0.8,
            linewidths=1.0,
            linecolor=THEME_BG,
            cbar_kws={"shrink": 0.8, "label": "Spearman Correlation Coefficient"},
            ax=ax,
        )
        ax.set_title("FraudShield AI — Feature Correlation Heatmap (Spearman Rank)", fontsize=13, fontweight="bold", pad=14)
        plt.tight_layout()
        dest = self.output_dir / "05_correlation_heatmap.png"
        fig.savefig(dest, dpi=300, bbox_inches="tight")
        plt.close(fig)
        return dest

    def plot_time_based_patterns(self) -> Path:
        """Chart 6: Diurnal 24-Hour Transaction Density."""
        fig, ax = plt.subplots(figsize=(12, 5))

        if "timestamp" in self.df.columns:
            ts = pd.to_datetime(self.df["timestamp"], utc=True)
            hours = ts.dt.hour

            if "is_fraud" in self.df.columns:
                legit_hours = hours[self.df["is_fraud"] == 0]
                fraud_hours = hours[self.df["is_fraud"] == 1]

                sns.kdeplot(legit_hours, ax=ax, color=COLOR_GREEN, linewidth=2.5, label="Legitimate Volume Density")
                sns.kdeplot(fraud_hours, ax=ax, color=COLOR_RED, linewidth=2.5, linestyle="--", label="Fraud Incident Density")

                # Highlight midnight danger zone
                ax.axvspan(1, 4.5, color=COLOR_AMBER, alpha=0.15, label="High-Risk Sleep Hours (01:00 - 05:00 AM)")

                ax.set_title("24-Hour Diurnal Pattern: Legitimate vs. Fraud Incident Density", fontsize=13, fontweight="bold", pad=12)
                ax.set_xlabel("Hour of the Day (0 - 23 UTC/IST)")
                ax.set_ylabel("Kernel Density Estimate")
                ax.set_xticks(range(0, 24))
                ax.legend(facecolor=THEME_CARD, edgecolor="#243046")
        else:
            ax.text(0.5, 0.5, "Timestamp data not available", ha="center", va="center")

        plt.tight_layout()
        dest = self.output_dir / "06_time_based_patterns.png"
        fig.savefig(dest, dpi=300, bbox_inches="tight")
        plt.close(fig)
        return dest

    def plot_outlier_analysis(self) -> Path:
        """Chart 7: Outlier Analysis via Boxplots and IQR Bounds."""
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        # Boxplot 1: Transaction Amount by Class
        if "is_fraud" in self.df.columns:
            sns.boxplot(
                data=self.df,
                x="is_fraud",
                y="amount",
                hue="is_fraud",
                legend=False,
                palette={0: COLOR_GREEN, 1: COLOR_RED},
                ax=axes[0],
                fliersize=3,
            )
            axes[0].set_title("Transaction Amount by Class (INR)", fontsize=12, fontweight="bold", pad=10)
            axes[0].set_xticks([0, 1])
            axes[0].set_xticklabels(["Legitimate (0)", "Fraudulent (1)"])
            axes[0].set_ylabel("Amount (INR)")

            # Boxplot 2: 15-Minute Velocity by Class
            if "velocity_15m" in self.df.columns:
                sns.boxplot(
                    data=self.df,
                    x="is_fraud",
                    y="velocity_15m",
                    hue="is_fraud",
                    legend=False,
                    palette={0: COLOR_GREEN, 1: COLOR_RED},
                    ax=axes[1],
                    fliersize=3,
                )
                axes[1].set_title("15-Minute Velocity Outliers by Class", fontsize=12, fontweight="bold", pad=10)
                axes[1].set_xticks([0, 1])
                axes[1].set_xticklabels(["Legitimate (0)", "Fraudulent (1)"])
                axes[1].set_ylabel("Transactions in Trailing 15 Min")

        plt.suptitle("FraudShield AI — Outlier & Anomaly Boundaries Analysis", fontsize=14, fontweight="bold", y=1.02)
        plt.tight_layout()
        dest = self.output_dir / "07_outlier_analysis.png"
        fig.savefig(dest, dpi=300, bbox_inches="tight")
        plt.close(fig)
        return dest

    def plot_summary_dashboard(self) -> Path:
        """Combined 4-panel Executive EDA Summary Dashboard."""
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))

        # Panel 1: Amount KDE
        sns.kdeplot(
            data=self.df,
            x="amount",
            hue="is_fraud",
            log_scale=True,
            palette={0: COLOR_GREEN, 1: COLOR_RED},
            common_norm=False,
            fill=True,
            alpha=0.3,
            ax=axes[0, 0],
        )
        axes[0, 0].set_title("1. Amount Density by Ground-Truth (Log)", fontweight="bold")

        # Panel 2: Channel Volume
        channel_counts = self.df["channel"].value_counts()
        axes[0, 1].pie(
            channel_counts.values,
            labels=channel_counts.index,
            autopct="%1.1f%%",
            colors=[COLOR_BLUE, COLOR_PURPLE, COLOR_CYAN, COLOR_AMBER],
            wedgeprops={"edgecolor": THEME_BG, "linewidth": 1.5},
            textprops={"color": THEME_TEXT},
        )
        axes[0, 1].set_title("2. Payment Channel Market Share", fontweight="bold")

        # Panel 3: Velocity by Class
        if "velocity_15m" in self.df.columns:
            sns.boxplot(
                data=self.df,
                x="is_fraud",
                y="velocity_15m",
                hue="is_fraud",
                legend=False,
                palette={0: COLOR_GREEN, 1: COLOR_RED},
                ax=axes[1, 0],
            )
            axes[1, 0].set_title("3. Transaction Velocity (15 Min Window)", fontweight="bold")
            axes[1, 0].set_xticks([0, 1])
            axes[1, 0].set_xticklabels(["Legit", "Fraud"])

        # Panel 4: Diurnal patterns
        if "timestamp" in self.df.columns:
            ts = pd.to_datetime(self.df["timestamp"], utc=True)
            hours = ts.dt.hour
            sns.histplot(
                data=self.df,
                x=hours,
                hue="is_fraud",
                multiple="dodge",
                bins=24,
                palette={0: COLOR_GREEN, 1: COLOR_RED},
                shrink=0.8,
                ax=axes[1, 1],
            )
            axes[1, 1].set_title("4. Hourly Transaction Volume (24h)", fontweight="bold")
            axes[1, 1].set_xlabel("Hour of Day")

        plt.suptitle("FraudShield AI — Executive Exploratory Data Analysis Dashboard", fontsize=15, fontweight="bold", y=0.99)
        plt.tight_layout()
        dest = self.output_dir / "eda_summary_dashboard.png"
        fig.savefig(dest, dpi=300, bbox_inches="tight")
        plt.close(fig)
        return dest


if __name__ == "__main__":
    visualizer = EDAVisualizer()
    generated_charts = visualizer.generate_all_visualisations()
    print("=" * 60)
    print("  FRAUDSHIELD AI — VISUALISATION GENERATION COMPLETE")
    print("=" * 60)
    for p in generated_charts:
        size_kb = round(p.stat().st_size / 1024, 1)
        print(f"  • {p.name:<38} ({size_kb} KB) -> {p.resolve()}")
    print("=" * 60)
