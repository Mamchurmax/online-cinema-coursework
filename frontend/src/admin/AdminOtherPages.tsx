/** Smaller admin sections: videos, payments, plans, users, ads. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link } from "react-router";

import type { Plan } from "../api/types";
import { useAuth } from "../auth/AuthProvider";
import { Pagination } from "../components/Pagination";
import { usePlans } from "../hooks/useAccount";
import { formatClock } from "../utils/format";
import { adminApi, errorText, type PlanInput } from "./api";

const dateTime = new Intl.DateTimeFormat("uk-UA", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

export function AdminVideosPage() {
  const queryClient = useQueryClient();
  const videos = useQuery({ queryKey: ["admin", "videos"], queryFn: adminApi.videos });
  const streams = useQuery({ queryKey: ["admin", "streams"], queryFn: adminApi.streams });
  const detach = useMutation({
    mutationFn: adminApi.detachVideo,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin"] }),
  });
  const used = new Set(videos.data?.map((v) => v.hls_path));

  return (
    <div className="admin__section">
      <h2 className="section-title section-title--compact">Прив'язані відео</h2>
      <table className="table">
        <thead>
          <tr><th>Тайтл</th><th>Епізод</th><th>Якості</th><th>Тривалість</th><th>HLS</th><th /></tr>
        </thead>
        <tbody>
          {videos.data?.map((video) => (
            <tr key={video.id}>
              <td><Link to={`/admin/titles/${video.title_id}`} className="link">{video.title}</Link></td>
              <td>{video.episode_label ?? "—"}</td>
              <td>{video.qualities.join(", ")}</td>
              <td>{formatClock(video.duration_sec)}</td>
              <td className="muted">{video.hls_path}</td>
              <td>
                <button className="button button--ghost button--small" onClick={() => detach.mutate(video.id)}>
                  Відв'язати
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2 className="section-title">Перекодовані папки (media/hls)</h2>
      <p className="muted">
        Нові відео перекодовуються скриптом <code>scripts/transcode.sh</code>, після чого з'являються тут. Прив'язати
        відео можна на сторінці тайтлу.
      </p>
      <ul className="admin-list">
        {streams.data?.map((s) => (
          <li key={s.directory}>
            <strong>{s.directory}</strong> · {s.qualities.join("/")} · {formatClock(s.duration_sec)}{" "}
            {used.has(s.hls_path) ? <span className="status status--succeeded">використовується</span> : <span className="muted">вільна</span>}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function AdminPaymentsPage() {
  const queryClient = useQueryClient();
  const pending = useQuery({ queryKey: ["admin", "payments"], queryFn: adminApi.pendingPayments, refetchInterval: 15_000 });
  const resolve = useMutation({
    mutationFn: ({ id, approved }: { id: number; approved: boolean }) => adminApi.resolvePayment(id, approved),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin", "payments"] }),
  });

  return (
    <div className="admin__section">
      <h2 className="section-title section-title--compact">Платежі, що очікують відповіді банку</h2>
      {pending.data?.length === 0 && <p className="muted">Черга порожня.</p>}
      {!!pending.data?.length && (
        <table className="table">
          <thead>
            <tr><th>№</th><th>Створено</th><th>Користувач</th><th>Тариф</th><th>Сума</th><th /></tr>
          </thead>
          <tbody>
            {pending.data.map((p) => (
              <tr key={p.id}>
                <td>{p.id}</td>
                <td>{dateTime.format(new Date(p.created_at))}</td>
                <td>{p.user_email}</td>
                <td>{p.plan.name}</td>
                <td>{Number(p.amount).toFixed(2)} грн</td>
                <td className="table__actions">
                  <button className="button button--small" disabled={resolve.isPending}
                          onClick={() => resolve.mutate({ id: p.id, approved: true })}>Підтвердити</button>
                  <button className="button button--ghost button--small" disabled={resolve.isPending}
                          onClick={() => resolve.mutate({ id: p.id, approved: false })}>Відхилити</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export function AdminPlansPage() {
  const plans = usePlans();
  return (
    <div className="admin__section">
      <h2 className="section-title section-title--compact">Тарифи</h2>
      <p className="muted">
        Політика перегляду визначається налаштуваннями: «Реклама» → FreePolicy, без реклами → PremiumPolicy (Strategy).
      </p>
      <div className="plans">{plans.data?.map((plan) => <PlanEditor key={plan.id} plan={plan} />)}</div>
    </div>
  );
}

function PlanEditor({ plan }: { plan: Plan }) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState<PlanInput>(plan);
  useEffect(() => setForm(plan), [plan]);
  const save = useMutation({
    mutationFn: () => adminApi.updatePlan(plan.id, form),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["plans"] }),
  });

  return (
    <form className="plan admin-form admin-form--compact" onSubmit={(e) => { e.preventDefault(); save.mutate(); }}>
      <span className="muted">Код: {plan.code}</span>
      <label className="field"><span className="field__label">Назва</span>
        <input className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
      </label>
      <label className="field"><span className="field__label">Ціна, грн</span>
        <input className="input" type="number" min={0} step={0.01} value={form.price}
               onChange={(e) => setForm({ ...form, price: e.target.value })} required />
      </label>
      <label className="field"><span className="field__label">Період, днів</span>
        <input className="input" type="number" min={1} max={366} value={form.period_days}
               onChange={(e) => setForm({ ...form, period_days: Number(e.target.value) })} required />
      </label>
      <label className="field"><span className="field__label">Макс. якість</span>
        <select className="input" value={form.max_quality} onChange={(e) => setForm({ ...form, max_quality: e.target.value })}>
          {["360p", "720p", "1080p"].map((q) => <option key={q}>{q}</option>)}
        </select>
      </label>
      <label className="scenario">
        <input type="checkbox" checked={form.has_ads} onChange={(e) => setForm({ ...form, has_ads: e.target.checked })} />
        <span>Реклама перед фільмом</span>
      </label>
      <button className="button" disabled={save.isPending}>Зберегти</button>
      {save.isSuccess && <span className="muted">Збережено ✓</span>}
      {save.isError && <span className="form-error">{errorText(save.error)}</span>}
    </form>
  );
}

export function AdminUsersPage() {
  const { user: me } = useAuth();
  const queryClient = useQueryClient();
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const users = useQuery({ queryKey: ["admin", "users", query, page], queryFn: () => adminApi.users(query, page) });
  const refresh = () => queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
  const setRole = useMutation({
    mutationFn: ({ id, role }: { id: number; role: "user" | "admin" }) => adminApi.setRole(id, role),
    onSuccess: refresh,
  });
  const remove = useMutation({ mutationFn: adminApi.deleteUser, onSuccess: refresh });
  const error = setRole.error ?? remove.error;

  return (
    <div className="admin__section">
      <div className="admin__toolbar">
        <input className="input admin__search" type="search" placeholder="Email або ім'я…" value={query}
               onChange={(e) => { setQuery(e.target.value); setPage(1); }} />
        <span className="muted">{users.data?.total ?? 0} користувачів</span>
      </div>
      {error && <p className="form-error">{errorText(error)}</p>}
      <table className="table">
        <thead>
          <tr><th>Email</th><th>Ім'я</th><th>Роль</th><th>Зареєстрований</th><th /></tr>
        </thead>
        <tbody>
          {users.data?.items.map((u) => (
            <tr key={u.id}>
              <td>{u.email}</td>
              <td>{u.display_name}</td>
              <td>
                <select className="input admin__narrow" value={u.role} disabled={u.id === me?.id}
                        onChange={(e) => setRole.mutate({ id: u.id, role: e.target.value as "user" | "admin" })}>
                  <option value="user">користувач</option>
                  <option value="admin">адміністратор</option>
                </select>
              </td>
              <td>{dateTime.format(new Date(u.created_at))}</td>
              <td>
                {u.id !== me?.id && (
                  <button className="button button--ghost button--small"
                          onClick={() => confirm(`Видалити ${u.email}?`) && remove.mutate(u.id)}>Видалити</button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {users.data && <Pagination page={page} pages={Math.ceil(users.data.total / users.data.page_size)} onChange={setPage} />}
    </div>
  );
}

export function AdminAdsPage() {
  const queryClient = useQueryClient();
  const ads = useQuery({ queryKey: ["admin", "ads"], queryFn: adminApi.ads });
  const streams = useQuery({ queryKey: ["admin", "streams"], queryFn: adminApi.streams });
  const refresh = () => queryClient.invalidateQueries({ queryKey: ["admin", "ads"] });
  const toggle = useMutation({
    mutationFn: ({ id, active }: { id: number; active: boolean }) => adminApi.setAdActive(id, active),
    onSuccess: refresh,
  });
  const [name, setName] = useState("");
  const [stream, setStream] = useState("");
  const create = useMutation({ mutationFn: () => adminApi.createAd(name, stream), onSuccess: refresh });

  return (
    <div className="admin__section">
      <h2 className="section-title section-title--compact">Реклама перед фільмом (тариф Free)</h2>
      <ul className="admin-list">
        {ads.data?.map((ad) => (
          <li key={ad.id}>
            <label className="scenario">
              <input type="checkbox" checked={ad.active} onChange={() => toggle.mutate({ id: ad.id, active: !ad.active })} />
              <span><strong>{ad.name}</strong><span className="muted">{ad.hls_path}</span></span>
            </label>
          </li>
        ))}
      </ul>
      <form className="admin__inline-form" onSubmit={(e) => { e.preventDefault(); create.mutate(); }}>
        <input className="input" placeholder="Назва ролика" value={name} onChange={(e) => setName(e.target.value)} required />
        <select className="input" value={stream} onChange={(e) => setStream(e.target.value)} required>
          <option value="">HLS-папка…</option>
          {streams.data?.map((s) => <option key={s.directory} value={s.directory}>{s.directory}</option>)}
        </select>
        <button className="button" disabled={create.isPending}>Додати ролик</button>
        {create.isError && <span className="form-error">{errorText(create.error)}</span>}
      </form>
    </div>
  );
}
