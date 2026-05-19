# -----------------------------------------------------------------------------
# SUMMARY:
# This script takes CSV files generated from a BMI propeller analysis and
# converts them into a color-coded Excel file.
#
# For each grid cell in the tables (best, 2nd-best, 3rd-best propeller),
# it fills the background color according to which propeller is listed.
#
# It also includes a legend sheet mapping each propeller to its assigned color.
# Output: "bmi_propeller_colored.xlsx"
# -----------------------------------------------------------------------------

import pandas as pd
import colorsys
import numpy as np

# Load the labeled CSV tables for best, second-best, and third-best propellers 
prop_best = pd.read_csv("bmi_best_propeller_labeled.csv")
prop_2nd = pd.read_csv("bmi_second_best_propeller_labeled.csv")
prop_3rd = pd.read_csv("bmi_third_best_propeller_labeled.csv")

# Remove the last row (contains duplicated velocity labels for reference)
prop_best = prop_best.iloc[:-1]
prop_2nd = prop_2nd.iloc[:-1]
prop_3rd = prop_3rd.iloc[:-1]

# Extract all unique propeller names from all three tables
all_values = pd.concat([
    prop_best.drop(columns="Thrust (N)"),
    prop_2nd.drop(columns="Thrust (N)"),
    prop_3rd.drop(columns="Thrust (N)")
]).values.ravel()  # Flatten to 1D array

# Remove empty strings and ensure uniqueness
unique_props = pd.unique(all_values)
unique_props = [p for p in unique_props if isinstance(p, str) and p.strip() != ""]

# Generate visually distinct colors for each propeller
def generate_colors(n):
    colors = []
    layers = int(np.ceil(n / 10))  # Group colors into layers with varied saturation and brightness
    for layer in range(layers):
        s = 0.6 + 0.2 * (layer % 2)       # Alternate saturation
        v = 1.0 - 0.1 * (layer // 2)      # Decrease brightness per layer
        for i in range(30):              # Spread across hue spectrum
            if len(colors) >= n:
                break
            h = i / 30
            rgb = colorsys.hsv_to_rgb(h, s, v)
            hex_color = '#{:02x}{:02x}{:02x}'.format(*(int(c * 255) for c in rgb))
            colors.append(hex_color)
    return colors

colors = generate_colors(len(unique_props))
prop_to_color = dict(zip(unique_props, colors))  # Map propeller name → hex color

# Helper function to write a color-coded Excel sheet
def write_colored_sheet(writer, df, sheet_name):
    workbook = writer.book
    df.to_excel(writer, sheet_name=sheet_name, index=False)
    worksheet = writer.sheets[sheet_name]

    # Start from the second row (index 1) to skip column headers
    # Start from the second column (index 1) to skip "Thrust (N)"
    for i, row in enumerate(df.itertuples(index=False), start=1):
        for j, val in enumerate(row[1:], start=1):  # Skip first column
            if isinstance(val, str) and val in prop_to_color:
                fmt = workbook.add_format({
                    'bg_color': prop_to_color[val],
                    'border': 1  # Add cell borders
                })
                worksheet.write(i, j, val, fmt)

# Create the Excel file with color-coded sheets
with pd.ExcelWriter("bmi_propeller_colored.xlsx", engine="xlsxwriter") as writer:
    # Write the three result tables with background colors
    write_colored_sheet(writer, prop_best, "Best Propeller")
    write_colored_sheet(writer, prop_2nd, "2nd Best Propeller")
    write_colored_sheet(writer, prop_3rd, "3rd Best Propeller")

    # Create a legend sheet showing which color corresponds to which propeller
    legend_df = pd.DataFrame({
        "Propeller": list(prop_to_color.keys()),
        "Color": list(prop_to_color.values())
    })
    legend_df.to_excel(writer, sheet_name="Legend", index=False)
    ws_legend = writer.sheets["Legend"]

    # Fill the color column with background colors
    for row_idx, color in enumerate(legend_df["Color"], start=1):  # Skip header
        fmt = writer.book.add_format({'bg_color': color})
        ws_legend.write(row_idx, 1, color, fmt)

print("Done: 'bmi_propeller_colored.xlsx' created.")
