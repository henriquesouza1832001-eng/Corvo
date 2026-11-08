import { useMemo } from "react";
import { geoGraticule10, geoNaturalEarth1, geoPath } from "d3-geo";
import { feature } from "topojson-client";
import type { FeatureCollection } from "geojson";
import world from "world-atlas/countries-110m.json";
import { ANCHORS, TOPIC_COLOR, type NewsItem, type Verdict } from "./model";

const W = 960;
const H = 500;

// A geometria do mundo é calculada uma vez: o mapa não depende de rede nem de biblioteca de mapas pesada.
const projection = geoNaturalEarth1().fitSize([W, H], { type: "Sphere" });
const path = geoPath(projection);
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const countries = feature(world as any, (world as any).objects.countries) as unknown as FeatureCollection;
const LAND = path(countries) ?? "";
const GRID = path(geoGraticule10()) ?? "";
const OUTLINE = path({ type: "Sphere" }) ?? "";

interface Props {
	items: { n: NewsItem; verdict: Verdict }[];
	selected: string | null;
	onSelect: (id: string | null) => void;
}

export function WorldMap({ items, selected, onSelect }: Props) {
	const markers = useMemo(
		() =>
			items
				.filter(({ n, verdict }) => verdict !== "drop" && n.lat != null && n.lon != null)
				.map(({ n, verdict }) => {
					const xy = projection([n.lon as number, n.lat as number]);
					return xy ? { n, verdict, x: xy[0], y: xy[1] } : null;
				})
				.filter((m): m is NonNullable<typeof m> => m !== null),
		[items],
	);
	const anchors = useMemo(() => ANCHORS.map((a) => ({ ...a, xy: projection([a.lon, a.lat]) })).filter((a) => a.xy), []);

	return (
		<svg className="map" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Mapa-múndi com ${markers.length} notícias localizadas`} onClick={() => onSelect(null)}>
			<path d={OUTLINE} className="map-sphere" />
			<path d={GRID} className="map-grid" />
			<path d={LAND} className="map-land" />
			{anchors.map((a) => (
				<g key={a.id} transform={`translate(${a.xy![0]},${a.xy![1]})`} className="anchor">
					<title>{`${a.label} (ponto de observação, coleta em preparação)`}</title>
					<rect x="-3" y="-3" width="6" height="6" transform="rotate(45)" />
				</g>
			))}
			{markers.map(({ n, verdict, x, y }) => {
				const color = TOPIC_COLOR[n.topics[0]] ?? "#39ff88";
				const r = 3 + n.relevance * 5;
				const on = selected === n.id;
				return (
					<g
						key={n.id}
						transform={`translate(${x},${y})`}
						className={`mk ${verdict}${on ? " on" : ""}`}
						style={{ color }}
						tabIndex={0}
						role="button"
						aria-label={`${n.region ?? ""}: ${n.title}`}
						onClick={(e) => { e.stopPropagation(); onSelect(n.id); }}
						onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onSelect(n.id); } }}
					>
						<circle className="ring" r={r} />
						<circle className="dot" r={r * 0.55} />
						<title>{`${n.region ?? ""} · ${n.title}`}</title>
					</g>
				);
			})}
		</svg>
	);
}
