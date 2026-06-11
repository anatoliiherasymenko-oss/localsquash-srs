/** Точка входу: запуск HTTP-сервера. PORT надає платформа розгортання (Render). */
const app = require("./app");

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`LocalSquash API запущено на порту ${PORT}`);
});
