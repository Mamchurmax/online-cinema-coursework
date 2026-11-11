interface PaginationProps {
  page: number;
  pages: number;
  onChange: (page: number) => void;
}

/** Page numbers around the current one, e.g. 1 … 4 5 [6] 7 8 … 20. */
function visiblePages(page: number, pages: number): (number | "gap")[] {
  const result: (number | "gap")[] = [];
  for (let p = 1; p <= pages; p++) {
    if (p === 1 || p === pages || Math.abs(p - page) <= 2) {
      result.push(p);
    } else if (result[result.length - 1] !== "gap") {
      result.push("gap");
    }
  }
  return result;
}

export function Pagination({ page, pages, onChange }: PaginationProps) {
  if (pages <= 1) return null;

  return (
    <nav className="pagination" aria-label="Сторінки">
      <button className="pagination__item" disabled={page <= 1} onClick={() => onChange(page - 1)}>
        ←
      </button>
      {visiblePages(page, pages).map((item, index) =>
        item === "gap" ? (
          <span key={`gap-${index}`} className="pagination__gap">
            …
          </span>
        ) : (
          <button
            key={item}
            className={`pagination__item ${item === page ? "pagination__item--active" : ""}`}
            aria-current={item === page ? "page" : undefined}
            onClick={() => onChange(item)}
          >
            {item}
          </button>
        ),
      )}
      <button className="pagination__item" disabled={page >= pages} onClick={() => onChange(page + 1)}>
        →
      </button>
    </nav>
  );
}
