import { useParams } from "react-router";

/** Placeholder: the title details page is the next step. */
export function TitlePage() {
  const { titleId } = useParams();

  return (
    <section>
      <h1 className="page-title">Тайтл #{titleId}</h1>
      <p className="muted">Тут буде сторінка фільму чи серіалу.</p>
    </section>
  );
}
