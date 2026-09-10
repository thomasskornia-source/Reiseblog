(function () {
  function initNotifyButtons() {
    var btns = document.querySelectorAll('.notify-btn');
    if (!btns.length || typeof window.OneSignalDeferred === 'undefined') return;

    window.OneSignalDeferred.push(async function (OneSignal) {
      async function refreshState() {
        var enabled = false;
        try {
          enabled = OneSignal.Notifications.permission === true ||
                    (await OneSignal.User.PushSubscription.optedIn);
        } catch (e) {}
        btns.forEach(function (btn) {
          btn.textContent = enabled ? '🔔 Benachrichtigungen aktiv' : '🔔 Benachrichtigungen aktivieren';
          btn.classList.toggle('subscribed', enabled);
        });
      }

      btns.forEach(function (btn) {
        btn.addEventListener('click', async function () {
          try {
            await OneSignal.Notifications.requestPermission();
          } catch (e) {}
          refreshState();
        });
      });

      refreshState();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initNotifyButtons);
  } else {
    initNotifyButtons();
  }
})();
