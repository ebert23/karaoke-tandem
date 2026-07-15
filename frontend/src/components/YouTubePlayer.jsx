import React, { forwardRef, useEffect, useImperativeHandle, useRef, useState } from "react";
import YouTube from "react-youtube";
import { extractVideoId } from "../lib/youtube.js";

// Envuelve react-youtube con controles imperativos (play/pause/+10s/volumen/
// fullscreen) y reporta progreso para timers sincronizados al video real
// (modo TV). Si el link no trae un ID reconocible, muestra un estado "sin
// video" en vez de romper — algunas canciones se agregan sin link.
const YouTubePlayer = forwardRef(function YouTubePlayer(
  { linkYoutube, autoplay = false, onEnd, onProgress },
  ref
) {
  const videoId = extractVideoId(linkYoutube);
  const playerRef = useRef(null);
  const contenedorRef = useRef(null);
  const progresoIntervalRef = useRef(null);
  const [listo, setListo] = useState(false);

  useImperativeHandle(ref, () => ({
    play: () => playerRef.current?.playVideo(),
    pause: () => playerRef.current?.pauseVideo(),
    seekForward10: () => {
      const p = playerRef.current;
      if (!p) return;
      p.seekTo(p.getCurrentTime() + 10, true);
    },
    setVolume: (v) => playerRef.current?.setVolume(v),
    requestFullscreen: () => contenedorRef.current?.requestFullscreen?.(),
  }));

  useEffect(() => {
    return () => clearInterval(progresoIntervalRef.current);
  }, []);

  function pausarSondeoProgreso() {
    clearInterval(progresoIntervalRef.current);
  }

  function iniciarSondeoProgreso() {
    pausarSondeoProgreso();
    if (!onProgress) return;
    progresoIntervalRef.current = setInterval(() => {
      const p = playerRef.current;
      if (!p) return;
      const duracion = p.getDuration();
      const transcurridos = p.getCurrentTime();
      if (duracion > 0) onProgress({ segundosTranscurridos: transcurridos, duracion });
    }, 1000);
  }

  function manejarListo(e) {
    playerRef.current = e.target;
    setListo(true);
  }

  function manejarCambioEstado(e) {
    // 1 = reproduciendo, 2 = pausado, 0 = terminado (YT.PlayerState)
    if (e.data === 1) iniciarSondeoProgreso();
    else pausarSondeoProgreso();
  }

  if (!videoId) {
    return (
      <div className="aspect-video rounded-xl bg-black/40 border border-white/10 flex items-center justify-center text-white/40 text-sm">
        Sin video disponible para esta canción
      </div>
    );
  }

  return (
    <div ref={contenedorRef} className="aspect-video rounded-xl overflow-hidden bg-black">
      <YouTube
        videoId={videoId}
        opts={{
          width: "100%",
          height: "100%",
          playerVars: { autoplay: autoplay ? 1 : 0, rel: 0, modestbranding: 1 },
        }}
        onReady={manejarListo}
        onStateChange={manejarCambioEstado}
        onEnd={() => {
          pausarSondeoProgreso();
          onEnd?.();
        }}
        className="w-full h-full"
        iframeClassName="w-full h-full"
      />
      {!listo && <p className="sr-only">Cargando video…</p>}
    </div>
  );
});

export default YouTubePlayer;
