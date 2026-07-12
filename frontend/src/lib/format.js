// Formatea el campo "Cantada por" (nombres separados por coma) en texto legible.
export function formatCantantes(cantadaPor) {
  const nombres = (cantadaPor || "")
    .split(",")
    .map((n) => n.trim())
    .filter(Boolean);
  if (nombres.length <= 1) return nombres[0] || "";
  if (nombres.length === 2) return `${nombres[0]} y ${nombres[1]}`;
  return `${nombres.slice(0, -1).join(", ")} y ${nombres[nombres.length - 1]}`;
}
