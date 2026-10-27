/* ControlGastos — comportamiento común de la interfaz.
   Todo el JavaScript vive en archivos .js: la CSP no permite scripts ni estilos en línea. */
"use strict";

(function () {
  const TABLETA = window.matchMedia("(min-width: 576px) and (max-width: 991.98px)");

  /* Colores y anchos variables definidos en atributos data-* */
  function aplicarEstilosDinamicos(raiz) {
    raiz.querySelectorAll("[data-cg-color]").forEach(function (elemento) {
      elemento.style.setProperty("--cg-color", elemento.dataset.cgColor);
    });
    raiz.querySelectorAll("[data-cg-color-texto]").forEach(function (elemento) {
      elemento.style.setProperty("--cg-color-texto", elemento.dataset.cgColorTexto);
    });
    raiz.querySelectorAll("[data-cg-ancho]").forEach(function (elemento) {
      elemento.style.width = elemento.dataset.cgAncho + "%";
    });
  }

  function mostrarToasts() {
    document.querySelectorAll(".cg-toast").forEach(function (elemento) {
      bootstrap.Toast.getOrCreateInstance(elemento).show();
    });
  }

  /* Tooltips de la barra lateral solo cuando está compacta (tableta) */
  function iniciarTooltipsCompactos() {
    const tooltips = Array.from(document.querySelectorAll("[data-cg-tooltip-compacto]")).map(function (elemento) {
      return new bootstrap.Tooltip(elemento);
    });
    function actualizar() {
      tooltips.forEach(function (tooltip) {
        if (TABLETA.matches) {
          tooltip.enable();
        } else {
          tooltip.hide();
          tooltip.disable();
        }
      });
    }
    actualizar();
    TABLETA.addEventListener("change", actualizar);
  }

  function iniciarAlternarContrasena() {
    document.querySelectorAll("[data-cg-alternar-contrasena]").forEach(function (boton) {
      const campo = document.getElementById(boton.dataset.cgAlternarContrasena);
      const icono = boton.querySelector(".bi");
      boton.addEventListener("click", function () {
        const mostrar = campo.type === "password";
        campo.type = mostrar ? "text" : "password";
        boton.setAttribute("aria-pressed", String(mostrar));
        boton.setAttribute("aria-label", mostrar ? "Ocultar contraseña" : "Mostrar contraseña");
        icono.classList.toggle("bi-eye", !mostrar);
        icono.classList.toggle("bi-eye-slash", mostrar);
      });
    });
  }

  /* Modal de confirmación único: el botón que lo abre define acción y textos */
  function iniciarModalConfirmacion() {
    const modal = document.getElementById("modalConfirmacion");
    if (!modal) {
      return;
    }
    const formulario = modal.querySelector("form");
    const titulo = modal.querySelector(".modal-title");
    const mensaje = modal.querySelector("[data-cg-modal-mensaje]");
    const boton = modal.querySelector("[data-cg-modal-boton]");
    modal.addEventListener("show.bs.modal", function (evento) {
      const origen = evento.relatedTarget;
      if (!origen) {
        return;
      }
      formulario.action = origen.dataset.cgAccion;
      titulo.textContent = origen.dataset.cgTitulo || "¿Confirmas esta acción?";
      mensaje.textContent = origen.dataset.cgMensaje || "";
      boton.textContent = origen.dataset.cgBoton || "Confirmar";
      const peligro = origen.hasAttribute("data-cg-peligro");
      boton.classList.toggle("btn-cg-peligro", peligro);
      boton.classList.toggle("btn-cg", !peligro);
    });
  }

  /* Contador de caracteres: data-cg-contador="id-del-contador" en el campo */
  function iniciarContadores() {
    document.querySelectorAll("[data-cg-contador]").forEach(function (campo) {
      const contador = document.getElementById(campo.dataset.cgContador);
      const maximo = campo.getAttribute("maxlength");
      function actualizar() {
        contador.textContent = campo.value.length + "/" + maximo;
      }
      campo.addEventListener("input", actualizar);
      actualizar();
    });
  }

  function iniciarCopiar() {
    document.querySelectorAll("[data-cg-copiar]").forEach(function (boton) {
      boton.addEventListener("click", function () {
        const texto = document.getElementById(boton.dataset.cgCopiar).textContent.trim();
        if (!navigator.clipboard) {
          return;
        }
        navigator.clipboard.writeText(texto).then(function () {
          boton.lastChild.textContent = " Copiada";
        });
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    aplicarEstilosDinamicos(document);
    mostrarToasts();
    iniciarTooltipsCompactos();
    iniciarAlternarContrasena();
    iniciarModalConfirmacion();
    iniciarContadores();
    iniciarCopiar();
  });

  window.ControlGastos = { aplicarEstilosDinamicos: aplicarEstilosDinamicos };
})();
