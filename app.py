fig, ax = plt.subplots()

# raw values (light, dashed)
ax.plot(
    plot_df["RecordedAt_dt"],
    plot_df["DeltaP"],
    linestyle="--",
    alpha=0.35,
    label="Raw"
)

# smoothed values (solid)
ax.plot(
    plot_df["RecordedAt_dt"],
    plot_df["DeltaP_smooth"],
    marker="o",
    label=f"Smoothed (window={win})"
)

ax.set_xlabel("Time")
ax.set_ylabel("Delta P (mmHg)")
ax.set_title("Delta P Trend")
ax.set_ylim(0, 100)
ax.legend()
fig.autofmt_xdate()
st.pyplot(fig, clear_figure=True)
