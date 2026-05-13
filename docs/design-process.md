# GPUMagick: UX Redesign Case Study

## Overview
GPUMagick is an internal tool built to analyze CPU bottlenecks based on GPU benchmark scores (FurMark, etc.) and aftermarket pricing. 

The original interface suffered from cognitive overload, inconsistent styling, and poor screen real estate utilization due to the limitations of standard Streamlit components. This document outlines the surgical UX audit and the structural redesign process applied to solve these issues.

## Global Consistency Fixes
Before tackling page-specific layouts, foundational UX debt was addressed across the app:
*   **Language Unification:** The UI was a mix of Spanish and English. A comprehensive audit replaced all UI strings with a standardized English glossary (e.g., *Muestras* → *Samples*, *Desv* → *Std*).
*   **State Persistence (Filters):** Context was lost when navigating between the "Analysis" and "Builds" pages. Filters (GPU, Benchmark, Resolution) were synced to `st.session_state`, ensuring seamless continuity.
*   **Visual Cohesion:** 
    *   **Dark Mode Tables:** Native Streamlit tables acted as "white flashbangs" on a dark theme. Solved by enforcing `base = "dark"` in `.streamlit/config.toml`.
    *   **Chart Palettes:** The "Builds" page used a blue gradient that broke the app's emerald green identity. Replaced with the standard `#4ade80` accent palette.
    *   **Contextual Sidebar:** Destructive actions (`Clear status`, `Kill scraper`) were globally visible. They were hidden from analytical pages and restricted exclusively to the "Scraper" context.

---

## Block 1: Scraper Page Redesign

### Problem
1. **Ambiguous Inputs:** Numeric inputs for the engine configuration lacked labels (hidden via `collapsed`).
2. **Action Button Dominance:** The `Execute` button spanned the entire width of the screen, taking up too much vertical space for a background process trigger.
3. **Table Spacing:** In the "Records in Database" table, the `cpu` column was unreadable due to uniform column collapsing.

### Solution
1. **Restored Labels:** Re-enabled native Streamlit labels with clear naming (`Start ID (Newest)`, `Concurrent workers`).
2. **Compact Action Center:** The `Execute` and `Stop` buttons were moved inside the configuration card, placed in a compact right-aligned column. This transformed the block into a cohesive "Control Panel".
3. **Column Config:** Applied `st.column_config.TextColumn(width="large")` to the `cpu` column, ensuring horizontal scroll kicks in before text truncates.

---

## Block 2: Analysis Page Redesign

### Problem
1. **Unclear Selection:** The "Sort by" segmented control blended into the background, making it impossible to tell which metric was active.
2. **Misaligned Heights:** The CPU stats table and the adjacent bar chart had different heights, creating a ragged layout.
3. **Cramped Padding:** The "Outliers" expander at the bottom was visually sticking to the main content above it.

### Solution
1. **Segmented Control Styling:** Injected CSS to style inactive buttons with a subtle outline and the active button with a solid accent background (`var(--ac)`), providing clear visual affordance.
2. **Height Unification:** Both the `st.dataframe` and the `make_bar` Plotly chart were hardcoded to `height=500` (or `420` proportionately) to create a perfect horizontal alignment.
3. **Breathing Room:** Added a 1.5rem spacer before the Outliers accordion to separate the analytical core from the edge-case data.

---

## Block 3: Builds Page Redesign (The Density Challenge)

### Problem
The "Builds" page had the highest cognitive load: 2 data editors (GPU and CPU prices), 1 large chart, 4 KPIs, and a massive results table, all fighting for attention. Furthermore, the action buttons ("Save prices") floated without context.

### Solution (Top-Bottom Asymmetric Layout)
Instead of relying on simple tabs or hiding the core price-editing feature, the page was entirely restructured using an asymmetric flow:

1. **Top Bar (Executive View):**
   *   A horizontal container acting as a control dashboard.
   *   Holds GPU selection, Filters, and the 4 main KPIs.
   *   *Technical Hurdle:* Since KPIs depend on price inputs (rendered below), `st.empty()` placeholders were used to inject the calculated metrics back to the top of the page.
2. **Bottom Split (1:2 Ratio):**
   *   **Left Column (Setup & Actions):** Groups all price configurations (GPU and CPU) and encapsulates the "Add to ranking" / "Save prices" buttons inside a clear, bordered **Action Center**.
   *   **Right Column (Visual Output):** Exclusively dedicated to the ranking bar chart, giving it the required width and importance.
3. **Hidden Complexity:** The raw "Full breakdown" table was relegated to an `st.expander` at the bottom, closed by default, dramatically reducing vertical scrolling and noise.