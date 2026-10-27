/* ControlGastos — dashboard P-02: tarjetas rápidas y gráficos con Chart.js 4 (sección 11.6).
   Los datos llegan por fetch a /api/dashboard; las cifras de los KPI ya vienen del servidor. */
"use strict";

(function () {
  const FORMATO = new Intl.NumberFormat("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  // En los ejes basta con soles enteros ("S/ 1,500"); los tooltips muestran céntimos
  const FORMATO_EJE = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });
  const COLORES = {
    texto: "#6B7280",
    rejilla: "#E5E7EB",
    real: "#111827",
    proyeccion: "#8B7BFF",
    presupuesto: "#9CA3AF",
  };
  const SIN_MOVIMIENTO = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function soles(valor) {
    return "S/ " + FORMATO.format(valor || 0);
  }

  /* ---------- Tarjetas rápidas: suman al monto y eligen la categoría (no guardan) ---------- */

  function leerMonto(texto) {
    let valor = (texto || "").replace("S/", "").replace(/\s/g, "");
    if (/^\d{1,3}(,\d{3})+(\.\d*)?$/.test(valor)) {
      valor = valor.replace(/,/g, "");
    } else if (/^\d+,\d{1,2}$/.test(valor)) {
      valor = valor.replace(",", ".");
    }
    const numero = parseFloat(valor);
    return isNaN(numero) || numero < 0 ? 0 : numero;
  }

  function iniciarTarjetasRapidas() {
    const monto = document.getElementById("rapido-monto");
    const categoria = document.getElementById("rapido-categoria");
    const anuncio = document.getElementById("rapido-anuncio");
    if (!monto || !categoria) {
      return;
    }
    function elegirCategoria(id) {
      if (categoria.querySelector('option[value="' + id + '"]')) {
        categoria.value = id;
      }
    }
    document.querySelectorAll("[data-cg-sumar]").forEach(function (boton) {
      boton.addEventListener("click", function () {
        const total = leerMonto(monto.value) + Number(boton.dataset.cgSumar);
        monto.value = total.toFixed(2);
        elegirCategoria(boton.dataset.cgRapidaCategoria);
        if (anuncio) {
          anuncio.textContent = "Monto: " + soles(total) + " en " + boton.dataset.cgRapidaNombre;
        }
      });
    });
    document.querySelectorAll("a[data-cg-rapida-categoria]").forEach(function (enlace) {
      enlace.addEventListener("click", function (evento) {
        evento.preventDefault();
        elegirCategoria(enlace.dataset.cgRapidaCategoria);
        monto.focus();
      });
    });
  }

  /* ---------- Gráficos ---------- */

  function configurarChart() {
    Chart.defaults.font.family = '"Inter", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif';
    Chart.defaults.font.size = 12;
    Chart.defaults.color = COLORES.texto;
    Chart.defaults.maintainAspectRatio = false;
    if (SIN_MOVIMIENTO) {
      Chart.defaults.animation = false;
    }
  }

  function ejeMontos(apilado, marcas) {
    return {
      stacked: Boolean(apilado),
      beginAtZero: true,
      grid: { color: COLORES.rejilla },
      border: { display: false },
      ticks: {
        maxRotation: 0,
        maxTicksLimit: marcas || 6,
        callback: function (valor) { return "S/ " + FORMATO_EJE.format(valor); },
      },
    };
  }

  function ejeEtiquetas(apilado, marcas) {
    return {
      stacked: Boolean(apilado),
      grid: { display: false },
      border: { display: false },
      ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: marcas || 31 },
    };
  }

  const TOOLTIP_SOLES = {
    callbacks: {
      label: function (contexto) {
        const nombre = contexto.dataset.label ? contexto.dataset.label + ": " : "";
        return nombre + soles(contexto.raw);
      },
    },
  };

  const graficos = {};
  let datosSemana = null;

  function dibujarSemana(datos) {
    datosSemana = datos;
    const conjuntos = datos.series.map(function (serie) {
      return {
        label: serie.categoria,
        data: serie.valores,
        backgroundColor: serie.color,
        borderRadius: 6,
        maxBarThickness: 28,
      };
    });
    if (graficos.semana) {
      graficos.semana.data.labels = datos.etiquetas;
      graficos.semana.data.datasets = conjuntos;
      graficos.semana.update();
    } else {
      graficos.semana = new Chart(document.getElementById("grafico-semana"), {
        type: "bar",
        data: { labels: datos.etiquetas, datasets: conjuntos },
        options: {
          scales: { x: ejeEtiquetas(true), y: ejeMontos(true) },
          plugins: { legend: { display: false }, tooltip: TOOLTIP_SOLES },
        },
      });
    }
    document.querySelector("[data-cg-semana-titulo]").textContent = datos.titulo;
    document.querySelector("[data-cg-semana-anterior]").dataset.cgSemana = datos.anterior;
    const siguiente = document.querySelector("[data-cg-semana-siguiente]");
    siguiente.disabled = !datos.siguiente;
    siguiente.dataset.cgSemana = datos.siguiente || "";
    llenarFiltro(datos);
    aplicarFiltro();
  }

  function llenarFiltro(datos) {
    const filtro = document.querySelector("[data-cg-filtro-semana]");
    const elegida = filtro.value;
    while (filtro.options.length > 1) {
      filtro.remove(1);
    }
    datos.series.forEach(function (serie) {
      filtro.add(new Option(serie.categoria, serie.categoria));
    });
    filtro.value = datos.series.some(function (serie) { return serie.categoria === elegida; }) ? elegida : "";
  }

  /* Leyenda HTML con punto de color, categoría y total, más la fila "Total" (textContent: sin HTML) */
  function dibujarLeyenda(datos, elegida) {
    const leyenda = document.querySelector("[data-cg-leyenda-semana]");
    leyenda.replaceChildren();
    function fila(nombre, total, color, clase) {
      const elemento = document.createElement("li");
      if (clase) {
        elemento.className = clase;
      }
      if (color) {
        const punto = document.createElement("span");
        punto.className = "cg-punto";
        punto.style.setProperty("--cg-color", color);
        elemento.appendChild(punto);
      }
      const etiqueta = document.createElement("span");
      etiqueta.className = "cg-leyenda__nombre";
      etiqueta.textContent = nombre;
      const valor = document.createElement("span");
      valor.className = "cg-leyenda__total cg-numero";
      valor.textContent = soles(total);
      elemento.append(etiqueta, valor);
      leyenda.appendChild(elemento);
    }
    const visibles = datos.series.filter(function (serie) { return !elegida || serie.categoria === elegida; });
    if (!visibles.length) {
      fila("Sin gastos esta semana", 0, null, "cg-leyenda__vacia");
      return;
    }
    visibles.forEach(function (serie) { fila(serie.categoria, serie.total, serie.color); });
    const total = visibles.reduce(function (suma, serie) { return suma + serie.total; }, 0);
    fila("Total", total, null, "cg-leyenda__fila-total");
  }

  function aplicarFiltro() {
    const elegida = document.querySelector("[data-cg-filtro-semana]").value;
    graficos.semana.data.datasets.forEach(function (conjunto, indice) {
      graficos.semana.setDatasetVisibility(indice, !elegida || conjunto.label === elegida);
    });
    graficos.semana.update();
    dibujarLeyenda(datosSemana, elegida);
  }

  function dibujarAcumulado(datos) {
    const conjuntos = [{
      label: "Gasto acumulado",
      data: datos.real,
      borderColor: COLORES.real,
      backgroundColor: COLORES.real,
      borderWidth: 2,
      pointRadius: 0,
    }];
    if (datos.proyeccion.some(function (valor) { return valor !== null; })) {
      conjuntos.push({
        label: "Proyección (estimación al ritmo actual)",
        data: datos.proyeccion,
        borderColor: COLORES.proyeccion,
        backgroundColor: COLORES.proyeccion,
        borderDash: [6, 5],
        borderWidth: 2,
        pointRadius: 0,
      });
    }
    if (datos.presupuesto) {
      conjuntos.push({
        label: "Presupuesto del mes",
        data: datos.etiquetas.map(function () { return datos.presupuesto; }),
        borderColor: COLORES.presupuesto,
        backgroundColor: COLORES.presupuesto,
        borderDash: [2, 3],
        borderWidth: 1.5,
        pointRadius: 0,
      });
    }
    const configuracion = {
      type: "line",
      data: { labels: datos.etiquetas, datasets: conjuntos },
      options: {
        interaction: { mode: "index", intersect: false },
        scales: { x: ejeEtiquetas(false, 11), y: ejeMontos(false) },
        plugins: {
          legend: { position: "bottom", labels: { boxWidth: 24, boxHeight: 2 } },
          tooltip: {
            filter: function (elemento) { return elemento.raw !== null; },
            callbacks: {
              title: function (elementos) { return "Día " + elementos[0].label; },
              label: TOOLTIP_SOLES.callbacks.label,
            },
          },
        },
      },
    };
    if (graficos.acumulado) {
      graficos.acumulado.destroy();
    }
    graficos.acumulado = new Chart(document.getElementById("grafico-acumulado"), configuracion);
  }

  function dibujarMetodos(datos) {
    const configuracion = {
      type: "bar",
      data: {
        labels: datos.etiquetas,
        datasets: [{ data: datos.valores, backgroundColor: datos.colores, borderRadius: 6, maxBarThickness: 24 }],
      },
      options: {
        indexAxis: "y",
        scales: { x: ejeMontos(false, 4), y: ejeEtiquetas(false) },
        plugins: { legend: { display: false }, tooltip: TOOLTIP_SOLES },
      },
    };
    if (graficos.metodos) {
      graficos.metodos.destroy();
    }
    graficos.metodos = new Chart(document.getElementById("grafico-metodos"), configuracion);
  }

  function mostrarError(hayError) {
    document.querySelectorAll("[data-cg-error-graficos]").forEach(function (elemento) { elemento.hidden = !hayError; });
    document.querySelectorAll("[data-cg-grafico]").forEach(function (elemento) { elemento.hidden = hayError; });
  }

  function cargar(contenedor, semana) {
    const url = new URL(contenedor.dataset.cgApi, window.location.origin);
    if (semana) {
      url.searchParams.set("semana", semana);
    }
    return fetch(url, { headers: { Accept: "application/json" }, credentials: "same-origin" })
      .then(function (respuesta) {
        if (!respuesta.ok) {
          throw new Error("Respuesta " + respuesta.status);
        }
        return respuesta.json();
      })
      .then(function (datos) {
        mostrarError(false);
        dibujarSemana(datos.semana);
        if (!semana) {
          dibujarAcumulado(datos.acumulado);
          dibujarMetodos(datos.metodos);
        }
      })
      .catch(function () {
        mostrarError(true);
      });
  }

  function iniciarGraficos() {
    const contenedor = document.querySelector("[data-cg-api]");
    if (!contenedor || !document.getElementById("grafico-semana") || typeof Chart === "undefined") {
      return;
    }
    configurarChart();
    document.querySelector("[data-cg-semana-anterior]").addEventListener("click", function (evento) {
      cargar(contenedor, evento.currentTarget.dataset.cgSemana);
    });
    document.querySelector("[data-cg-semana-siguiente]").addEventListener("click", function (evento) {
      if (evento.currentTarget.dataset.cgSemana) {
        cargar(contenedor, evento.currentTarget.dataset.cgSemana);
      }
    });
    document.querySelector("[data-cg-filtro-semana]").addEventListener("change", aplicarFiltro);
    document.querySelectorAll("[data-cg-reintentar]").forEach(function (boton) {
      boton.addEventListener("click", function () { cargar(contenedor); });
    });
    cargar(contenedor);
  }

  document.addEventListener("DOMContentLoaded", function () {
    iniciarTarjetasRapidas();
    iniciarGraficos();
  });
})();
