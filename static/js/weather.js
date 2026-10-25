const WEATHER_URL = "https://api.open-meteo.com/v1/forecast?latitude=7.2906&longitude=80.6337"
    + "&current=temperature_2m,weather_code&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max"
    + "&timezone=Asia%2FColombo&forecast_days=1";

function weatherName(code) {
    if (code === 0) return ["Clear sky", "sun"];
    if (code <= 2) return ["Partly cloudy", "sun"];
    if (code === 3) return ["Cloudy", "cloud"];
    if (code <= 48) return ["Foggy", "cloud"];
    if (code <= 57) return ["Drizzle", "rain"];
    if (code <= 67) return ["Rain", "rain"];
    if (code <= 77) return ["Cold showers", "rain"];
    if (code <= 82) return ["Rain showers", "rain"];
    return ["Thunderstorms", "rain"];
}

async function loadWeather() {
    const card = document.getElementById("weather");
    const text = document.getElementById("weatherText");
    const more = document.getElementById("weatherMore");
    try {
        const response = await fetch(WEATHER_URL, { signal: AbortSignal.timeout(6000) });
        if (!response.ok) throw new Error(response.status);
        const data = await response.json();
        const [name, sky] = weatherName(data.current.weather_code);
        const rain = data.daily.precipitation_probability_max[0];

        document.getElementById("weatherTemp").textContent = `${Math.round(data.current.temperature_2m)}°`;
        if (!rain) text.textContent = name;
        else text.textContent = sky === "rain" ? `${name} · ${rain}%` : `${name} · ${rain}% rain`;
        more.textContent += ` · ${Math.round(data.daily.temperature_2m_max[0])}° / ${Math.round(data.daily.temperature_2m_min[0])}°`;
        card.dataset.sky = sky;
    } catch (error) {
        text.textContent = "Weather unavailable";
    }
}

loadWeather();
