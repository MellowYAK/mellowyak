const locale = new URLSearchParams(window.location.search).get("lang") === "he" ? "he" : "en";
const messages = await fetch(`/translations/${locale}.json`).then((response) => response.json());
document.documentElement.lang = locale;
document.documentElement.dir = locale === "he" ? "rtl" : "ltr";
for (const element of document.querySelectorAll("[data-i18n]")) {
  element.textContent = messages[element.dataset.i18n];
}
