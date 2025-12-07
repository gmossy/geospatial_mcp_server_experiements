# Grand Canyon Terrain Demo

You now have real elevation data for the Grand Canyon loaded!

## 1. Ask Claude

Try these prompts to see the power of the Geo MCP server:

**"What is the elevation at 36.1, -112.1?"**
> It should return ~734 meters.

**"Show me a heatmap of the terrain at 36.1, -112.1."**
> Claude will display a generated image of the canyon floor/rim.

**"Do I have line of sight from the rim (36.06, -112.14) to the river (36.10, -112.10)?"**
> It will calculate the profile and tell you if terrain blocks the view.

**"Find a spot near 36.1, -112.1 that is at least 800m high."**
> Claude can use the tools to sample points or reason about the terrain.

## 2. Verify Locally

I generated a heatmap image locally for you to see what Claude sees.
Open **`grand_canyon_heatmap.png`** in Windsurf to see the terrain visualization.
