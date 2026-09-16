import React from "react";
import { youtubeWatchUrl } from "../lib/youtube.js";

function IconCast(props) {
  return (
    <svg viewBox="0 0 24 24" width={18} height={18} fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" {...props}>
      <path d="M4 18.5a1.5 1.5 0 0 1 1.5 1.5" />
      <path d="M4 14a6 6 0 0 1 6 6" />
      <path d="M4 9.5A10.5 10.5 0 0 1 14.5 20" />
      <path d="M8 4h10a2 2 0 0 1 2 2v10" />
    </svg>
  );
}

export default function CastYoutubeButton({ linkYoutube }) {
  const href = youtubeWatchUrl(linkYoutube);
  if (!href) return null;

  return (
    <div className="mt-3">
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="btn-ghost w-full justify-center !border-red-400/35 hover:!border-red-300/60 hover:!text-white"
        aria-describedby="cast-youtube-help"
      >
        <IconCast aria-hidden="true" /> Proyectar a TV
      </a>
      <p id="cast-youtube-help" className="text-white/35 text-xs mt-2 leading-relaxed">
        Se abrirá YouTube. Toca el ícono Cast y elige tu Chromecast o Smart TV en la misma red wifi.
      </p>
    </div>
  );
}
