/* MerlionOS service worker — Web Push receiver.
 * Kept tiny and single-purpose: show the pushed alert, and focus/open the app when it's clicked.
 * Served from the site root so its scope covers the whole app. */

self.addEventListener("push", (event) => {
    let data = { title: "MerlionOS alert", body: "" };
    try {
        if (event.data) data = event.data.json();
    } catch (e) {
        if (event.data) data.body = event.data.text();
    }
    const title = data.title || "MerlionOS alert";
    const options = {
        body: data.body || "",
        icon: "/merlion-icon.png",
        badge: "/merlion-icon.png",
        tag: data.tag || undefined,      // same tag replaces an earlier notification instead of stacking
        data: { url: data.url || "/" },
    };
    event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
    event.notification.close();
    const url = (event.notification.data && event.notification.data.url) || "/";
    event.waitUntil(
        clients.matchAll({ type: "window", includeUncontrolled: true }).then((wins) => {
            // Focus an existing tab if the app is already open; otherwise open a new one.
            for (const w of wins) {
                if ("focus" in w) return w.focus();
            }
            if (clients.openWindow) return clients.openWindow(url);
        })
    );
});
