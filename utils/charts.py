import plotly.express as px

def make_bar(df, x, y, color_scale, text_fmt="%{text:,.0f}", height=400):
    fig = px.bar(df, x=x, y=y, orientation="h",
                 template="plotly_dark", color=x,
                 color_continuous_scale=color_scale, text=x)
    fig.update_traces(
        texttemplate=text_fmt, textposition="outside",
        textfont=dict(family="JetBrains Mono", size=11, color="#ddddf0"),
        marker_line_width=0,
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", color="#6868a0"),
        showlegend=False, coloraxis_showscale=False,
        margin=dict(l=0, r=70, t=8, b=0), height=height,
        xaxis=dict(showgrid=True, gridcolor="#1e1e30", zeroline=False,
                   tickfont=dict(size=10, family="JetBrains Mono")),
        yaxis=dict(showgrid=False, tickfont=dict(size=11, family="Inter")),
    )
    return fig
