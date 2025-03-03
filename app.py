from dash import Dash, html, dcc, Input, Output
import plotly.express as px
import dash_bootstrap_components as dbc
import pandas as pd
from pandas_datareader import wb


app = Dash(__name__, external_stylesheets=[dbc.themes.SPACELAB])

indicators = {
    "SP.URB.TOTL.IN.ZS": "Urban population (% of total population)",
    "AG.LND.FRST.ZS": "Forest area (% of land area)",
    "AG.LND.AGRI.ZS": "Agricultural land (% of land area)",
}

# country name & iso3c id for choropleth map
countries = wb.get_countries()
countries.replace({"capitalCity": {"": None}}, inplace=True)
countries.dropna(subset=["capitalCity"], inplace=True)
countries = countries[["name", "iso3c"]]
countries = countries[countries["name"] != "Kosovo"]
countries.rename(columns={"name": "country"})


# retrieve world bank data
def update_wb_data():
    df = wb.download(
        indicator=list(indicators),
        country=countries["iso3c"],
        start=1990,
        end=2022,
    )

    df = df.reset_index()
    df.year = df.year.astype(int)

    countries_renamed = countries.rename(columns={"name": "country"})

    df = pd.merge(df, countries_renamed, on="country")
    df = df.rename(columns=indicators)
    df = df.reset_index(drop=True)

    return df


app.layout = dbc.Container(
    [
        dbc.Row(
            dbc.Col(
                [
                    html.H1("Urbanization in the World Over Time", style={"textAlign": "center"}),
                    dcc.Graph(id="my-choropleth", figure={}),
                ],
                width=12,
            )
        ),
        dbc.Row(
            dbc.Col(
                [
                    dbc.Label("Select Year:", className="fw-bold", style={"textDecoration": "underline", "fontSize": 20}),
                    dcc.Slider(
                        id="year-slider",
                        min=1990,
                        max=2022,
                        step=1,
                        value=1990,
                        marks={year: str(year) for year in range(1990, 2023)},
                    ),
                ],
                width=12,
            )
        ),
        dbc.Row(
            dbc.Col(
                [
                    html.Hr(),
                    html.H4("Click on a region to compare the following data:"),
                    dcc.Graph(id="combined-bar-chart", figure={}),
                ],
                width=12,
            )
        ),
        dcc.Store(id="storage", storage_type="session", data={}),
    ]
)


@app.callback(
    Output("storage", "data"),
    [Input("my-choropleth", "clickData"),
     Input("year-slider", "value")]
)
def update_data(click_data, selected_year):
    # init. stored_data if it's none
    stored_data = {"clicked_regions": [], "year": selected_year}

    # only update stored data if click_data exists
    if click_data:
        country_iso = click_data['points'][0]['location']
        if country_iso not in stored_data['clicked_regions']:
            stored_data['clicked_regions'].append(country_iso)

    # store year chosen
    stored_data['year'] = selected_year

    return stored_data


@app.callback(
    Output("my-choropleth", "figure"),
    [Input("year-slider", "value")]
)
def update_choropleth(selected_year):
    # load stored data
    df = update_wb_data()
    df = df[df['year'] == selected_year]

    choropleth_fig = px.choropleth(
        df,
        locations="iso3c",
        color="Urban population (% of total population)",
        hover_name="country",
        hover_data={"iso3c": False, "country": False, "Urban population (% of total population)": True},
        labels={"Urban population (% of total population)": "Urban Population (%)"},
        color_continuous_scale="plasma",
        title=f"Urban population in {selected_year}"
    )

    choropleth_fig.update_layout(
        geo={"projection": {"type": "natural earth"}},
    )

    return choropleth_fig


@app.callback(
    Output("combined-bar-chart", "figure"),
    [Input("my-choropleth", "clickData"),
     Input("year-slider", "value")]
)
def update_combined_bar(click_data, selected_year):
    if not click_data:
        return px.bar(title="Click a region to see data.")

    clicked_country = click_data['points'][0]['location']
    df = update_wb_data()
    df = df[df['year'] == selected_year]


    df_selected = df[df['iso3c'] == clicked_country]
    print(f"Clicked Country: {clicked_country}")
    print(f"ISO3 codes in DataFrame: {df['iso3c'].unique()}")

    if df_selected.empty:
        return px.bar(title="No data available.")

    country_name = df_selected.iloc[0]["country"]
    data = {
        "Category": ["Forest Area (%)", "Agricultural Land (%)"],
        "Percentage": [
            df_selected.iloc[0]["Forest area (% of land area)"],
            df_selected.iloc[0]["Agricultural land (% of land area)"]
        ]
    }

    fig = px.bar(
        data,
        x="Category",
        y="Percentage",
        title=f"Forest vs. Agricultural Land - {country_name} ({selected_year})",
        color="Category",
        color_discrete_map={
            "Forest Area (%)": "green",
            "Agricultural Land (%)": "#800020",
        }
    )

    fig.update_layout(
        bargap=0.5,
        bargroupgap=0,
        yaxis=dict(range=[0, 100]),
        xaxis_title="Land Use",
        yaxis_title="Percentage"
    )

    return fig


if __name__ == "__main__":
    app.run_server(debug=True)
