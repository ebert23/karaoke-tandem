// 15s: la app ya viene rozando la cuota de lecturas de Google Sheets, así
// que el sondeo de sesión activa (Karaoke.jsx, TV.jsx) va despacio para no
// sumar presión extra (la votación en vivo sondea aparte, cada 4s).
export const POLL_MS = 15000;
