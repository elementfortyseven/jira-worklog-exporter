/* global React */
const { useState, useEffect, useRef, useCallback } = React;

/* ---------- tiny inline icons (simple geometry only) ---------- */
const I = {
  logo: (
    <svg width="15" height="15" viewBox="0 0 16 16" fill="none">
      <rect x="2.5" y="2.5" width="8" height="8" rx="1.6" stroke="#22d3ee" strokeWidth="1.4" />
      <rect x="5.5" y="5.5" width="8" height="8" rx="1.6" fill="#22d3ee" fillOpacity="0.18" stroke="#22d3ee" strokeWidth="1.4" />
    </svg>
  ),
  min: <svg width="12" height="12" viewBox="0 0 12 12"><line x1="2.5" y1="6" x2="9.5" y2="6" stroke="currentColor" strokeWidth="1.3" /></svg>,
  max: <svg width="12" height="12" viewBox="0 0 12 12"><rect x="2.5" y="2.5" width="7" height="7" rx="1" stroke="currentColor" strokeWidth="1.2" fill="none" /></svg>,
  close: <svg width="12" height="12" viewBox="0 0 12 12"><line x1="3" y1="3" x2="9" y2="9" stroke="currentColor" strokeWidth="1.3" /><line x1="9" y1="3" x2="3" y2="9" stroke="currentColor" strokeWidth="1.3" /></svg>,
  plug: <svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"><path d="M5 8h6M8 5v6" opacity="0" /><path d="M10.5 5.5 13 3M3 13l2.5-2.5M6 10l-2 2a2.1 2.1 0 0 1-3-3l2-2M10 6l2-2a2.1 2.1 0 0 1 3 3l-2 2M6.5 9.5l3-3" /></svg>,
  users: <svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3"><circle cx="6" cy="5" r="2.4" /><path d="M2 13c0-2.2 1.8-3.6 4-3.6S10 10.8 10 13" /><path d="M10.5 3.2A2.4 2.4 0 0 1 12 7.4M11 9.6c1.8.2 3 1.6 3 3.4" strokeLinecap="round" /></svg>,
  cal: <svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3"><rect x="2.2" y="3.2" width="11.6" height="10.6" rx="1.8" /><path d="M2.2 6.2h11.6M5.2 2v2.4M10.8 2v2.4" strokeLinecap="round" /></svg>,
  out: <svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"><path d="M8 2.5v7M5.2 7l2.8 2.8L10.8 7" /><path d="M2.8 11v1.5a1 1 0 0 0 1 1h8.4a1 1 0 0 0 1-1V11" /></svg>,
  search: <svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4"><circle cx="7" cy="7" r="4.2" /><line x1="10.2" y1="10.2" x2="13.5" y2="13.5" strokeLinecap="round" /></svg>,
  eye: <svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3"><path d="M1.5 8S4 3.5 8 3.5 14.5 8 14.5 8 12 12.5 8 12.5 1.5 8 1.5 8Z" /><circle cx="8" cy="8" r="1.8" /></svg>,
  eyeOff: <svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"><path d="M3 3l10 10M6.3 6.4A1.8 1.8 0 0 0 8 9.8M2 8s2.5-4.5 6-4.5c1 0 1.9.3 2.7.7M13.4 6c.6.8 1.1 2 1.1 2S12 12.5 8 12.5c-.5 0-1-.1-1.4-.2" /></svg>,
  check: <svg width="11" height="11" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M2.5 6.2 5 8.6l4.5-5" /></svg>,
  folder: <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3"><path d="M2 4.2A1 1 0 0 1 3 3.2h3l1.3 1.4h5.7a1 1 0 0 1 1 1V12a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V4.2Z" /></svg>,
  file: <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3"><path d="M4 2.2h5l3 3V13a.8.8 0 0 1-.8.8H4a.8.8 0 0 1-.8-.8V3a.8.8 0 0 1 .8-.8Z" /><path d="M9 2.2V5.4h3" /></svg>,
  play: <svg width="13" height="13" viewBox="0 0 14 14" fill="currentColor"><path d="M3.5 2.4 11 7l-7.5 4.6V2.4Z" /></svg>,
};

const STR = {
  de: {
    title: ["Jira ", "Worklog", " Exporter"],
    connectedAs: "Verbunden als", ready: "Bereit zum Export", fillReq: "Pflichtfelder ausfüllen, um zu exportieren",
    s1: "Verbindung", s1sub: "Authentifizierung gegen Jira Cloud",
    sa: "Service-Account", usr: "Persönliches Token",
    siteUrl: "Site-URL", discover: "Ermitteln", cloudId: "Cloud-ID", email: "E-Mail", token: "API-Token", authHeader: "Auth-Header",
    saveToken: "Token im Schlüsselbund speichern", testConn: "Verbindung testen", testing: "Verbindung wird getestet …", connected: "Verbunden",
    s2: "Nutzer", s2sub: "Worklog-Autoren auswählen", searchPh: "Nutzer suchen (Name oder E-Mail) …",
    results: "Suchergebnisse", selected: "Ausgewählt", needConn: "Erst Verbindung testen, um zu suchen", noResults: "Keine Treffer", noneSelected: "Noch niemand ausgewählt",
    s3: "Zeitraum & Projekt", s3sub: "Filter für die Worklog-Abfrage", from: "Von", to: "Bis", projects: "Projekte", projectsPh: "z. B. PROJ, SUPP", projectsHint: "optional · leer = alle sichtbaren Projekte",
    s4: "Ausgabe", s4sub: "Format und Zielverzeichnis der CSV", outDir: "Zielordner", browse: "Durchsuchen", delimiter: "Trennzeichen", profile: "Spaltenprofil", apiV: "API-Version",
    startExport: "Export starten", cancel: "Abbrechen",
    issues: "Issues", worklogs: "Worklogs", exportDone: "Export abgeschlossen", openCsv: "CSV öffnen", openFolder: "Ordner öffnen",
    comma: ", (Komma)", semi: "; (Semikolon)",
  },
  en: {
    title: ["Jira ", "Worklog", " Exporter"],
    connectedAs: "Connected as", ready: "Ready to export", fillReq: "Fill in required fields to export",
    s1: "Connection", s1sub: "Authenticate against Jira Cloud",
    sa: "Service account", usr: "Personal token",
    siteUrl: "Site URL", discover: "Discover", cloudId: "Cloud ID", email: "Email", token: "API token", authHeader: "Auth header",
    saveToken: "Save token to keyring", testConn: "Test connection", testing: "Testing connection …", connected: "Connected",
    s2: "Users", s2sub: "Pick the worklog authors", searchPh: "Search users (name or email) …",
    results: "Search results", selected: "Selected", needConn: "Test the connection to search", noResults: "No matches", noneSelected: "No one selected yet",
    s3: "Date & project", s3sub: "Filters for the worklog query", from: "From", to: "To", projects: "Projects", projectsPh: "e.g. PROJ, SUPP", projectsHint: "optional · empty = all visible projects",
    s4: "Output", s4sub: "Format and target folder of the CSV", outDir: "Output folder", browse: "Browse", delimiter: "Delimiter", profile: "Column profile", apiV: "API version",
    startExport: "Start export", cancel: "Cancel",
    issues: "Issues", worklogs: "Worklogs", exportDone: "Export complete", openCsv: "Open CSV", openFolder: "Open folder",
    comma: ", (comma)", semi: "; (semicolon)",
  },
};

const MOCK_USERS = [
  { id: "5b10a2844c2a1e3f001", name: "Martin Brandt", mail: "martin.brandt@acme.com", in: "MB" },
  { id: "5c11b3955617a8002", name: "Lena Hoffmann", mail: "lena.hoffmann@acme.com", in: "LH" },
  { id: "5d22c4066728b9003", name: "Tobias Krüger", mail: "tobias.krueger@acme.com", in: "TK" },
  { id: "5e33d5177839c0004", name: "Aylin Demir", mail: "aylin.demir@acme.com", in: "AD" },
  { id: "5f44e6288940d1005", name: "Jonas Weber", mail: "jonas.weber@acme.com", in: "JW" },
  { id: "6a55f7399051e2006", name: "Sophie Vogel", mail: "sophie.vogel@acme.com", in: "SV" },
];

function Section({ icon, num, title, sub, end, children }) {
  return (
    <div className="sect">
      <div className="sect__head">
        <div className="sect__icon">{icon}</div>
        <div className="sect__head-tx">
          <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
            <span className="sect__num">{num}</span>
            <span className="sect__title">{title}</span>
          </div>
          <span className="sect__sub">{sub}</span>
        </div>
        {end ? <div className="sect__head-end">{end}</div> : null}
      </div>
      {children}
    </div>
  );
}

function Field({ label, hint, children }) {
  return (
    <label className="field">
      <span className="field__label">{label}</span>
      {children}
      {hint ? <span className="field__hint">{hint}</span> : null}
    </label>
  );
}

function AppWindow({ variant = "restrained", initialLang = "de", initialState = null }) {
  const seeded = initialState === "connected" || initialState === "done";
  const [lang, setLang] = useState(initialLang);
  const t = STR[lang];

  const [mode, setMode] = useState("sa");
  const [showToken, setShowToken] = useState(false);
  const [saveToken, setSaveToken] = useState(true);
  const [authHeader, setAuthHeader] = useState("basic");
  const [conn, setConn] = useState(seeded ? "ok" : "idle"); // idle | testing | ok | err
  const [creds, setCreds] = useState(
    seeded
      ? { url: "https://acme.atlassian.net", cloud: "1a11d016-8984-4c3e-b9ab-142dd06acb1b", email: "jwe-bot@serviceaccount.atlassian.com", token: "scoped-token", siteUrl: "", siteEmail: "", siteToken: "" }
      : { url: "", cloud: "", email: "", token: "", siteUrl: "", siteEmail: "", siteToken: "" }
  );

  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(seeded ? MOCK_USERS.slice(0, 3) : []);
  const [picked, setPicked] = useState(null);

  const [projects, setProjects] = useState(initialState === "done" ? ["PROJ", "SUPP"] : []);
  const [projInput, setProjInput] = useState("");

  const [phase, setPhase] = useState(initialState === "done" ? "done" : "idle"); // idle | running | done
  const [counts, setCounts] = useState(initialState === "done" ? { i: 128, w: 814 } : { i: 0, w: 0 });
  const [logLines, setLogLines] = useState(
    initialState === "done"
      ? [
          { c: "ac", x: "\u203a JQL: worklogAuthor in (3 users) AND worklogDate >= 2026-05-01 AND project in (PROJ, SUPP)" },
          { c: "t", x: "  128 Issues verarbeitet \u00b7 814 Worklogs" },
          { c: "ok", x: "\u2713 Fertig \u2014 jira_worklogs_2026-05-01_2026-05-31.csv" },
        ]
      : []
  );
  const logRef = useRef(null);

  const setCred = (k, v) => setCreds((c) => ({ ...c, [k]: v }));

  /* ---- connection test (demo: always succeeds) ---- */
  const testConn = useCallback(() => {
    if (conn === "testing") return;
    setConn("testing");
    setTimeout(() => setConn("ok"), 1150);
  }, [conn]);

  /* ---- user search results ---- */
  const q = query.trim().toLowerCase();
  const selIds = new Set(selected.map((u) => u.id));
  const results = conn === "ok" && q
    ? MOCK_USERS.filter((u) => !selIds.has(u.id) && (u.name.toLowerCase().includes(q) || u.mail.toLowerCase().includes(q)))
    : [];

  const addUser = (u) => { setSelected((s) => [...s, u]); setPicked(null); };
  const removeUser = (u) => setSelected((s) => s.filter((x) => x.id !== u.id));

  /* ---- projects chips ---- */
  const commitProj = () => {
    const parts = projInput.split(",").map((p) => p.trim().toUpperCase()).filter(Boolean);
    if (parts.length) setProjects((p) => [...new Set([...p, ...parts])]);
    setProjInput("");
  };

  /* ---- export flow ---- */
  const canExport = conn === "ok" && selected.length > 0 && phase !== "running";
  const startExport = () => {
    if (!canExport) return;
    setPhase("running");
    setCounts({ i: 0, w: 0 });
    setLogLines([
      { c: "ac", x: "› JQL: worklogAuthor in (" + selected.length + " users) AND worklogDate >= " + (lang === "de" ? "2026-05-01" : "2026-05-01") },
      { c: "t", x: lang === "de" ? "  Suche nach passenden Issues …" : "  Searching matching issues …" },
    ]);
  };

  useEffect(() => {
    if (phase !== "running") return;
    let i = 0, w = 0;
    const tot = { i: 128, w: 814 };
    const iv = setInterval(() => {
      i = Math.min(tot.i, i + Math.round(tot.i / 24));
      w = Math.min(tot.w, w + Math.round(tot.w / 24));
      setCounts({ i, w });
      if (i >= tot.i && w >= tot.w) {
        clearInterval(iv);
        setTimeout(() => {
          setLogLines((l) => [
            ...l,
            { c: "t", x: (lang === "de" ? "  " + tot.i + " Issues verarbeitet · " : "  " + tot.i + " issues processed · ") + tot.w + " Worklogs" },
            { c: "ok", x: (lang === "de" ? "✓ Fertig — " : "✓ Done — ") + "jira_worklogs_2026-05-01_2026-05-31.csv" },
          ]);
          setPhase("done");
        }, 350);
      }
    }, 130);
    return () => clearInterval(iv);
  }, [phase, lang]);

  useEffect(() => { if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight; }, [logLines]);

  /* reset downstream state when connection invalidated */
  useEffect(() => { if (conn !== "ok") { setSelected([]); setQuery(""); setPhase("idle"); } }, [conn]);

  return (
    <div className="jwe" data-variant={variant}>
      {/* ===== TITLE BAR ===== */}
      <div className="jwe__titlebar">
        <div className="jwe__brand">
          <div className="jwe__logo">{I.logo}</div>
          <div className="jwe__title">{t.title[0]}<b>{t.title[1]}</b>{t.title[2]}</div>
        </div>
        <div className="jwe__titlebar-spacer" />
        <div className="jwe__lang">
          <button className={lang === "de" ? "is-on" : ""} onClick={() => setLang("de")}>DE</button>
          <button className={lang === "en" ? "is-on" : ""} onClick={() => setLang("en")}>EN</button>
        </div>
        <div className="jwe__winctl">
          <button className="jwe__winbtn">{I.min}</button>
          <button className="jwe__winbtn">{I.max}</button>
          <button className="jwe__winbtn is-close">{I.close}</button>
        </div>
      </div>

      {/* ===== IDENTITY STRIP (when connected) ===== */}
      {conn === "ok" && (
        <div className="jwe__idstrip">
          <span className="dot" />
          <span>{t.connectedAs} <b>jwe-bot</b></span>
          <span className="mono">accountId 712020:4f8c…a91</span>
        </div>
      )}

      {/* ===== BODY ===== */}
      <div className="jwe__body">
        {/* --- 01 Connection --- */}
        <Section
          icon={I.plug} num="01" title={t.s1} sub={t.s1sub}
          end={
            <div className="seg">
              <button className={"seg__btn" + (mode === "sa" ? " is-on" : "")} onClick={() => setMode("sa")}>{t.sa}</button>
              <button className={"seg__btn" + (mode === "user" ? " is-on" : "")} onClick={() => setMode("user")}>{t.usr}</button>
            </div>
          }
        >
          <div className="field-rows">
            {mode === "sa" ? (
              <>
                <Field label={t.siteUrl}>
                  <div className="with-btn">
                    <input className="input" placeholder="https://acme.atlassian.net" value={creds.url} onChange={(e) => setCred("url", e.target.value)} />
                    <button className="btn">{t.discover}</button>
                  </div>
                </Field>
                <div className="grid-2">
                  <Field label={t.cloudId}>
                    <input className="input input--mono" placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" value={creds.cloud} onChange={(e) => setCred("cloud", e.target.value)} />
                  </Field>
                  <Field label={t.email}>
                    <input className="input" placeholder="bot@serviceaccount.atlassian.com" value={creds.email} onChange={(e) => setCred("email", e.target.value)} />
                  </Field>
                </div>
                <div className="grid-2">
                  <Field label={t.token}>
                    <div className="input-wrap">
                      <input className="input" type={showToken ? "text" : "password"} placeholder="••••••••••••••••" value={creds.token} onChange={(e) => setCred("token", e.target.value)} />
                      <button className="input-eye" onClick={() => setShowToken((s) => !s)}>{showToken ? I.eyeOff : I.eye}</button>
                    </div>
                  </Field>
                  <Field label={t.authHeader}>
                    <div className="select-wrap">
                      <select className="select" value={authHeader} onChange={(e) => setAuthHeader(e.target.value)}>
                        <option value="basic">Basic</option>
                        <option value="bearer">Bearer</option>
                      </select>
                    </div>
                  </Field>
                </div>
              </>
            ) : (
              <>
                <Field label={t.siteUrl}>
                  <input className="input" placeholder="https://acme.atlassian.net" value={creds.siteUrl} onChange={(e) => setCred("siteUrl", e.target.value)} />
                </Field>
                <div className="grid-2">
                  <Field label={t.email}>
                    <input className="input" placeholder="you@example.com" value={creds.siteEmail} onChange={(e) => setCred("siteEmail", e.target.value)} />
                  </Field>
                  <Field label={t.token}>
                    <div className="input-wrap">
                      <input className="input" type={showToken ? "text" : "password"} placeholder="••••••••••••••••" value={creds.siteToken} onChange={(e) => setCred("siteToken", e.target.value)} />
                      <button className="input-eye" onClick={() => setShowToken((s) => !s)}>{showToken ? I.eyeOff : I.eye}</button>
                    </div>
                  </Field>
                </div>
              </>
            )}

            <div style={{ display: "flex", alignItems: "center", gap: 16, marginTop: 2 }}>
              <button className={"check" + (saveToken ? " is-on" : "")} onClick={() => setSaveToken((s) => !s)}>
                <span className="check__box">{I.check}</span>{t.saveToken}
              </button>
              <div style={{ flex: 1 }} />
              <button className="btn btn--primary" onClick={testConn} disabled={conn === "testing"}>
                {conn === "testing" ? <span className="spin" /> : I.plug}{t.testConn}
              </button>
              {conn === "ok" && <span className="chip chip--ok"><span className="dot" />{t.connected} · jwe-bot</span>}
              {conn === "testing" && <span className="chip chip--testing">{t.testing}</span>}
            </div>
          </div>
        </Section>

        {/* --- 02 Users --- */}
        <Section icon={I.users} num="02" title={t.s2} sub={t.s2sub}
          end={selected.length > 0 ? <span className="chip">{selected.length} {t.selected.toLowerCase()}</span> : null}>
          <div className="searchbar">
            {I.search}
            <input className="input" placeholder={t.searchPh} value={query} onChange={(e) => setQuery(e.target.value)} disabled={conn !== "ok"} />
          </div>
          <div className="shuttle">
            <div className="userlist">
              <div className="userlist__head">{t.results}</div>
              {conn !== "ok" ? (
                <div className="userlist__empty">{t.needConn}</div>
              ) : results.length === 0 ? (
                <div className="userlist__empty">{q ? t.noResults : "—"}</div>
              ) : results.map((u) => (
                <div key={u.id} className={"user" + (picked === u.id ? " is-sel" : "")} onClick={() => setPicked(u.id)} onDoubleClick={() => addUser(u)}>
                  <div className="user__avatar">{u.in}</div>
                  <div className="user__tx"><div className="user__name">{u.name}</div><div className="user__mail">{u.mail}</div></div>
                </div>
              ))}
            </div>
            <div className="shuttle__ctrl">
              <button className="arrow-btn" onClick={() => { const u = results.find((r) => r.id === picked); if (u) addUser(u); }}>›</button>
              <button className="arrow-btn" onClick={() => { if (selected.length) removeUser(selected[selected.length - 1]); }}>‹</button>
            </div>
            <div className="userlist">
              <div className="userlist__head">{t.selected}</div>
              {selected.length === 0 ? (
                <div className="userlist__empty">{t.noneSelected}</div>
              ) : selected.map((u) => (
                <div key={u.id} className="user is-sel" onDoubleClick={() => removeUser(u)}>
                  <div className="user__avatar">{u.in}</div>
                  <div className="user__tx"><div className="user__name">{u.name}</div><div className="user__mail">{u.mail}</div></div>
                </div>
              ))}
            </div>
          </div>
        </Section>

        {/* --- 03 Date & project --- */}
        <Section icon={I.cal} num="03" title={t.s3} sub={t.s3sub}>
          <div className="date-grid">
            <Field label={t.from}><input className="input input--mono" defaultValue="2026-05-01" /></Field>
            <Field label={t.to}><input className="input input--mono" defaultValue="2026-05-31" /></Field>
            <Field label={t.projects} hint={t.projectsHint}>
              <input className="input" placeholder={t.projectsPh} value={projInput}
                onChange={(e) => setProjInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" || e.key === ",") { e.preventDefault(); commitProj(); } }}
                onBlur={commitProj} />
            </Field>
          </div>
          {projects.length > 0 && (
            <div className="chips">
              {projects.map((p) => (
                <span key={p} className="pchip">{p}<button onClick={() => setProjects((x) => x.filter((y) => y !== p))}>×</button></span>
              ))}
            </div>
          )}
        </Section>

        {/* --- 04 Output --- */}
        <Section icon={I.out} num="04" title={t.s4} sub={t.s4sub}>
          <div className="field-rows">
            <Field label={t.outDir}>
              <div className="with-btn">
                <input className="input input--mono" defaultValue="C:\\Users\\martin\\Documents\\exports" />
                <button className="btn">{I.folder}{t.browse}</button>
              </div>
            </Field>
            <div className="grid-3">
              <Field label={t.delimiter}>
                <div className="select-wrap"><select className="select"><option>{t.comma}</option><option>{t.semi}</option></select></div>
              </Field>
              <Field label={t.profile}>
                <div className="select-wrap"><select className="select" defaultValue="standard"><option value="minimal">minimal</option><option value="standard">standard</option><option value="full">full</option></select></div>
              </Field>
              <Field label={t.apiV}>
                <div className="select-wrap"><select className="select"><option>3</option><option>2</option></select></div>
              </Field>
            </div>
          </div>
        </Section>
      </div>

      {/* ===== FOOTER / EXPORT BAR ===== */}
      <div className="jwe__footer">
        {phase === "idle" && (
          <div className="footer__main">
            <button className="btn btn--primary btn--lg" onClick={startExport} disabled={!canExport}>{I.play}{t.startExport}</button>
            <div className="footer__status">
              {canExport
                ? <><span className="chip chip--ok"><span className="dot" />{t.ready}</span></>
                : <span className="req">{t.fillReq}</span>}
            </div>
          </div>
        )}

        {phase === "running" && (
          <div className="footer__panel">
            <div className="footer__main">
              <div className="counters">
                <div className="counter"><span className="counter__n">{counts.i}</span><span className="counter__l">{t.issues}</span></div>
                <div className="counter"><span className="counter__n">{counts.w}</span><span className="counter__l">{t.worklogs}</span></div>
              </div>
              <div className="footer__spacer" />
              <button className="btn btn--ghost">{t.cancel}</button>
            </div>
            <div className="progress"><div className="progress__bar" /></div>
            <div className="log" ref={logRef}>{logLines.map((l, k) => <div key={k} className={l.c}>{l.x}</div>)}<span className="log__caret" /></div>
          </div>
        )}

        {phase === "done" && (
          <div className="footer__panel">
            <div className="footer__main">
              <div className="counters">
                <div className="counter"><span className="counter__n">{counts.i}</span><span className="counter__l">{t.issues}</span></div>
                <div className="counter"><span className="counter__n">{counts.w}</span><span className="counter__l">{t.worklogs}</span></div>
              </div>
              <div className="footer__spacer" />
              <button className="btn btn--primary" onClick={startExport}>{I.play}{t.startExport}</button>
            </div>
            <div className="progress"><div className="progress__bar is-done" /></div>
            <div className="results">
              <span className="results__done"><span className="badge">{I.check}</span>{t.exportDone}<span className="results__path">jira_worklogs_2026-05-01_2026-05-31.csv</span></span>
              <button className="btn">{I.file}{t.openCsv}</button>
              <button className="btn">{I.folder}{t.openFolder}</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

window.AppWindow = AppWindow;
