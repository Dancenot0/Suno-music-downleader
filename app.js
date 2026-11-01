/* Suno v1 — comportamiento mínimo: revelado al hacer scroll, versión
   desde GitHub y año del pie. Sin dependencias. */
(() => {
  "use strict";

  /* ---------- aparición al hacer scroll ---------- */
  const reveals = document.querySelectorAll(".reveal");
  const reducir = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  if (reducir || !("IntersectionObserver" in window)) {
    reveals.forEach((el) => el.classList.add("in"));
  } else {
    const io = new IntersectionObserver(
      (entradas) => {
        entradas.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add("in");
            io.unobserve(e.target);
          }
        });
      },
      { rootMargin: "0px 0px -8% 0px", threshold: 0.08 }
    );
    reveals.forEach((el) => io.observe(el));
  }

  /* red de seguridad: si el observador se retrasa, lo visible no se queda oculto */
  setTimeout(() => {
    document.querySelectorAll(".reveal:not(.in)").forEach((el) => {
      if (el.getBoundingClientRect().top < window.innerHeight * 1.1) el.classList.add("in");
    });
  }, 900);

  /* ---------- año del pie ---------- */
  const year = document.getElementById("year");
  if (year) year.textContent = String(new Date().getFullYear());

  /* ---------- versión y descarga ----------
     Los instaladores se sirven desde esta misma web (descargas/), así que no
     hace falta compilar para quien descarga. Las versiones se escriben aquí y
     en el HTML; al publicar una nueva, se sustituye el archivo y se actualiza
     el número. Escritorio y móvil llevan ritmos distintos. */
  const verWin = document.getElementById("ver-win");
  const verAndroid = document.getElementById("ver-android");
  const VERSION = "1.2.3";
  const VERSION_ANDROID = "1.3.6";

  if (verWin) verWin.textContent = VERSION;
  if (verAndroid) verAndroid.textContent = VERSION_ANDROID;

  /* ---------- sombra al bajar ---------- */
  const nav = document.getElementById("nav");
  if (nav) {
    const aplicar = () => nav.classList.toggle("pegado", window.scrollY > 8);
    aplicar();
    window.addEventListener("scroll", aplicar, { passive: true });
  }
})();
