// 20s: la app ya viene rozando la cuota de lecturas de Google Sheets, así
// que el sondeo de sesión activa (Karaoke.jsx, TV.jsx) va despacio para no
// sumar presión extra — más aún ahora que Karaoke y el Modo TV suelen
// quedar abiertos en pestañas separadas al mismo tiempo, duplicando las
// lecturas (la votación en vivo sondea aparte, cada 6s).
export const POLL_MS = 20000;
