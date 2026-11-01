/* Suno v1 — comportamiento mínimo: revelado al hacer scroll, versión
   desde GitHub y año del pie. Sin dependencias. */
(() => {
  "use strict";

  const REPO = "Dancenot0/Suno-music-downleader";
  const VERSION_FALLBACK = "1.1.0";

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

  /* ---------- año del pie ---------- */
  const year = document.getElementById("year");
  if (year) year.textContent = String(new Date().getFullYear());

  /* ---------- versión y enlace real del .msi ---------- */
  const ver1 = document.getElementById("ver-1");
  const ver2 = document.getElementById("ver-2");
  const btn = document.getElementById("dl-msi");

  function pintarVersion(v) {
    if (!v) return;
    if (ver1) ver1.textContent = "v" + v;
    if (ver2) ver2.textContent = v;
  }

  async function mirarUltimaVersion() {
    try {
      const r = await fetch(`https://api.github.com/repos/${REPO}/releases/latest`, {
        headers: { Accept: "application/vnd.github+json" },
      });
      if (!r.ok) return; // repo privado, sin releases o sin red: se queda el valor por defecto
      const datos = await r.json();
      const tag = String(datos.tag_name || "").replace(/^v/i, "");
      pintarVersion(tag || VERSION_FALLBACK);

      const msi = (datos.assets || []).find((a) => a.name.toLowerCase().endsWith(".msi"));
      if (msi && btn) {
        btn.href = msi.browser_download_url;
        btn.removeAttribute("target");
        btn.removeAttribute("rel");
      }
    } catch {
      /* sin conexión: los valores por defecto ya están puestos */
    }
  }

  pintarVersion(VERSION_FALLBACK);
  mirarUltimaVersion();

  /* ---------- sombra al bajar ---------- */
  const nav = document.getElementById("nav");
  if (nav) {
    const aplicar = () => nav.classList.toggle("pegado", window.scrollY > 8);
    aplicar();
    window.addEventListener("scroll", aplicar, { passive: true });
  }
})();
