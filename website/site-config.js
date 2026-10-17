/* Public settings for the website. This file is public: never put secrets in it.
   apiBase : the address of your running SAGE server (no trailing slash).
             On localhost it automatically uses http://localhost:8000. If you change the hosted address, also add it to connect-src in the Content-Security-Policy
             of chat/index.html and mobile/index.html, and to SAGE_CORS_ORIGINS on the server.
   email / phone / phoneLabel : optional public contact details. Empty values stay hidden. */
(function () {
  /* On your own computer (localhost) the page talks to your own server. Anywhere else it uses the hosted server. */
  var onThisComputer = ["localhost", "127.0.0.1"].indexOf(window.location.hostname) !== -1;
window.SITE = {
  apiBase: onThisComputer ? "http://" + window.location.hostname + ":8000" : "https://sage-one-api.onrender.com",
  email: "",
  phone: "",
  phoneLabel: ""
};
})();
