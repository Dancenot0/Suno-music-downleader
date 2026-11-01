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
     El instalador se sirve desde esta misma web (docs/descargas/), así que no
     hace falta compilar ni pasar por Releases. La versión se escribe aquí y en
     el HTML; al publicar una nueva, se sustituye el .msi y se actualiza el
     número. */
  const ver1 = document.getElementById("ver-1");
  const ver2 = document.getElementById("ver-2");
  const VERSION = "1.1.0";

  if (ver1) ver1.textContent = "v" + VERSION;
  if (ver2) ver2.textContent = VERSION;

  /* ---------- sombra al bajar ---------- */
  const nav = document.getElementById("nav");
  if (nav) {
    const aplicar = () => nav.classList.toggle("pegado", window.scrollY > 8);
    aplicar();
    window.addEventListener("scroll", aplicar, { passive: true });
  }
})();
