import type { AqiShape } from "../lib/aqi";

interface Props {
  shape: AqiShape;
  color: string;
  size?: number;
  title?: string;
}

// Custom SVG glyphs (never emoji — see DESIGN.md Anti-Slop Checklist). These give
// every AQI category a distinct silhouette so color is never the only signal (G4).
const PATHS: Record<AqiShape, string> = {
  circle: "M12 4a8 8 0 1 0 0 16 8 8 0 0 0 0-16Z",
  triangle: "M12 3 21 20H3L12 3Z",
  diamond: "M12 2 22 12 12 22 2 12 12 2Z",
  square: "M4 4h16v16H4z",
  pentagon: "M12 2 22 9.3 18.2 21H5.8L2 9.3 12 2Z",
  hexagon: "M7 3h10l5 9-5 9H7l-5-9 5-9Z",
};

export function CategoryShape({ shape, color, size = 14, title }: Props) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      role={title ? "img" : "presentation"}
      aria-label={title}
      aria-hidden={title ? undefined : true}
    >
      <path d={PATHS[shape]} fill={color} stroke="rgba(7,10,18,0.55)" strokeWidth="1" />
    </svg>
  );
}
