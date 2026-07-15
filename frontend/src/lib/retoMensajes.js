// Mensajes divertidos que aparecen antes de revelar un reto. Lista abierta —
// agregar más strings acá alcanza, no hace falta tocar nada más.
const MENSAJES = [
  // Épicos
  "¡ATENCIÓN, ATENCIÓN! 🎤 ¡Es hora del RETO! Prepárate, valiente…",
  "¡EL KARAOKE SE PONE SERIO! 🔥 ¡Hora del Reto!",
  "¡LUZ, CÁMARA… RETO! 📸 El público exige espectáculo.",
  // Con humor
  "¡SORPRESA! 😂 El karaoke decidió que ya estabas muy cómodo…",
  "¡MOMENTO VIRAL ACTIVADO! 📱 Hora del Reto. Si lo cumples, te hacemos famoso.",
  "¡PELIGRO! 😈 El reto ha elegido a su próxima víctima…",
  // Cortos
  "¡HORA DEL RETO! 🎲 ¡A darle con todo!",
  "¡RETO ACTIVADO! 🔥 ¿Aceptas el desafío?",
  "¡QUE EMPIECE EL SHOW! 🎭 Reto en 3… 2… 1…",
  // Picantes
  "¡AVISO PICANTE! 🌶️ Hora del Reto… que no te tiemblen las piernas.",
  "¡MODO SIN VERGÜENZA ACTIVADO! 😏 ¡Sin censura!",
  // Más
  "¡CÓDIGO ROJO! 🚨 El micrófono acaba de elegir a su siguiente víctima…",
  "¡SE ACABÓ LA TREGUA! ⚡ Hora del Reto — nadie se salva.",
  "¡EL DESTINO HA HABLADO! 🔮 Y dice que te toca sufrir un poquito…",
  "¡ALERTA DE VERGÜENZA! 🙈 Prepará la sonrisa, viene el Reto.",
  "¡BASTA DE CANTAR TRANQUILO! 🎉 Es hora de complicarte la noche.",
];

export function mensajeAleatorio() {
  return MENSAJES[Math.floor(Math.random() * MENSAJES.length)];
}
