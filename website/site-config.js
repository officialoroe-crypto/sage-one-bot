/* Public settings for the website. This file is public: never put secrets in it.
   apiBase : the address of your running SAGE server (no trailing slash).
             If you change the host, also add it to connect-src in the Content-Security-Policy
             of chat/index.html and mobile/index.html, and to SAGE_CORS_ORIGINS on the server.
   email / phone / phoneLabel : optional public contact details. Empty values stay hidden. */
window.SITE = {
  apiBase: "https://sage-one-api.onrender.com",
  email: "",
  phone: "",
  phoneLabel: ""
};
