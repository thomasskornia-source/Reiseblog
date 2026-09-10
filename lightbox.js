(function () {
  function initLightbox() {
    var imgs = document.querySelectorAll('.photo .frame img');
    if (!imgs.length) return;

    var images = Array.prototype.map.call(imgs, function (img) {
      return { src: img.getAttribute('src'), alt: img.getAttribute('alt') || '' };
    });

    var overlay = document.createElement('div');
    overlay.className = 'lightbox-overlay';
    overlay.innerHTML =
      '<button class="lightbox-close" aria-label="Schließen">&times;</button>' +
      '<button class="lightbox-prev" aria-label="Vorheriges Foto">&#8249;</button>' +
      '<img class="lightbox-img" alt="">' +
      '<button class="lightbox-next" aria-label="Nächstes Foto">&#8250;</button>' +
      '<div class="lightbox-counter"></div>';
    document.body.appendChild(overlay);

    var imgEl = overlay.querySelector('.lightbox-img');
    var counterEl = overlay.querySelector('.lightbox-counter');
    var current = 0;

    function show(idx) {
      current = (idx + images.length) % images.length;
      imgEl.src = images[current].src;
      imgEl.alt = images[current].alt;
      counterEl.textContent = (current + 1) + ' / ' + images.length;
    }

    function open(idx) {
      show(idx);
      overlay.classList.add('open');
      document.body.style.overflow = 'hidden';
    }

    function close() {
      overlay.classList.remove('open');
      document.body.style.overflow = '';
    }

    imgs.forEach(function (img, idx) {
      img.addEventListener('click', function () { open(idx); });
    });

    overlay.querySelector('.lightbox-close').addEventListener('click', close);
    overlay.querySelector('.lightbox-prev').addEventListener('click', function () { show(current - 1); });
    overlay.querySelector('.lightbox-next').addEventListener('click', function () { show(current + 1); });
    overlay.addEventListener('click', function (e) { if (e.target === overlay) close(); });

    document.addEventListener('keydown', function (e) {
      if (!overlay.classList.contains('open')) return;
      if (e.key === 'Escape') close();
      if (e.key === 'ArrowLeft') show(current - 1);
      if (e.key === 'ArrowRight') show(current + 1);
    });

    var touchStartX = null;
    overlay.addEventListener('touchstart', function (e) {
      touchStartX = e.touches[0].clientX;
    }, { passive: true });
    overlay.addEventListener('touchend', function (e) {
      if (touchStartX === null) return;
      var dx = e.changedTouches[0].clientX - touchStartX;
      if (Math.abs(dx) > 40) {
        dx < 0 ? show(current + 1) : show(current - 1);
      }
      touchStartX = null;
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initLightbox);
  } else {
    initLightbox();
  }
})();
