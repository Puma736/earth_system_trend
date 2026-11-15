export const dynamic = "force-dynamic";

const USER_AGENT = "DetectiveTendencias/0.1 (nasa_space; educational local use)";

interface NominatimHit {
  place_id: number | string;
  display_name: string;
  lat: string;
  lon: string;
}

export async function GET(request: Request): Promise<Response> {
  const query = new URL(request.url).searchParams.get("q")?.trim() ?? "";
  if (query.length < 3 || query.length > 120) return Response.json([]);

  const endpoint = new URL("https://nominatim.openstreetmap.org/search");
  endpoint.searchParams.set("format", "jsonv2");
  endpoint.searchParams.set("q", query);
  endpoint.searchParams.set("limit", "5");
  endpoint.searchParams.set("countrycodes", "bo");
  endpoint.searchParams.set("addressdetails", "0");

  try {
    const response = await fetch(endpoint, {
      headers: {
        Accept: "application/json",
        "Accept-Language": "es",
        "User-Agent": USER_AGENT,
      },
      cache: "no-store",
      signal: AbortSignal.timeout(8000),
    });
    if (!response.ok) {
      return Response.json({ error: "El buscador de lugares no respondió." }, { status: 502 });
    }
    const payload = (await response.json()) as NominatimHit[];
    const results = payload
      .map((hit) => {
        const name = hit.display_name.split(",")[0]?.trim() || hit.display_name;
        return {
          id: String(hit.place_id),
          name,
          label: hit.display_name,
          lat: Number(hit.lat),
          lon: Number(hit.lon),
        };
      })
      .filter((hit) => hit.name && Number.isFinite(hit.lat) && Number.isFinite(hit.lon));
    return Response.json(results);
  } catch {
    return Response.json({ error: "No se pudo consultar el lugar." }, { status: 502 });
  }
}
