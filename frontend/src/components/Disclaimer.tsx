/**
 * HL4 — the app shows AQI category + EPA descriptor only and must carry a
 * persistent "not medical guidance" notice on any forecast/alert surface.
 */
export function Disclaimer() {
  return (
    <p className="text-xs leading-relaxed text-mist-500">
      Informational forecast — <strong className="text-mist-400">not medical guidance</strong>. Air
      Quality Index categories follow the US EPA scale; consult official sources for health
      decisions.
    </p>
  );
}
