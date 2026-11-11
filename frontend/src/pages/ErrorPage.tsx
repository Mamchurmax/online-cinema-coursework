import { isRouteErrorResponse, Link, useRouteError } from "react-router";

export function ErrorPage() {
  const error = useRouteError();
  const notFound = isRouteErrorResponse(error) && error.status === 404;

  return (
    <section className="container main error-page">
      <h1 className="page-title">{notFound ? "Сторінку не знайдено" : "Щось пішло не так"}</h1>
      <p className="muted">
        {notFound ? "Такої сторінки немає." : "Спробуйте оновити сторінку трохи пізніше."}
      </p>
      <Link to="/" className="button">
        До каталогу
      </Link>
    </section>
  );
}
