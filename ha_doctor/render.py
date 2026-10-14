"""Offline reports. Escape all user-controlled strings before writing HTML."""

from html import escape
import json
from .diagnose import Report


def text_report(report: Report) -> str:
    lines = ["", "🩺 HA DOCTOR — DIAGNOSTIC REPORT", "═" * 51,
             f"Home Assistant: {report.version} | Entities: {report.entity_count} | Samples: {report.samples}",
             f"Unavailable: {report.unavailable_count} | Unknown: {report.unknown_count}", ""]
    if not report.findings:
        lines.append("✓ No problems detected by the enabled checks.")
    for finding in report.findings:
        icon = {"critical": "!!", "warning": "!", "info": "i"}[finding.severity]
        lines += [f"[{icon}] {finding.title}  ({finding.code})", f"    {finding.detail}",
                  f"    Next: {finding.action}"]
        if finding.entities:
            lines.append("    Entities: " + ", ".join(finding.entities[:12]) +
                         (f" … +{len(finding.entities) - 12} more" if len(finding.entities) > 12 else ""))
        lines.append("")
    lines += ["NOTES:"] + ["  • " + note for note in report.observations]
    return "\n".join(lines) + "\n"


def html_report(report: Report) -> str:
    def e(s):
        return escape(str(s), quote=True)
    badges = "".join(
        f'<article class="stat"><span>{e(label)}</span><strong>{e(value)}</strong></article>'
        for label, value in [
            ("Entities", report.entity_count), ("Unavailable", report.unavailable_count),
            ("Unknown", report.unknown_count), ("Samples", report.samples)])
    cards = []
    for finding in report.findings:
        # Do not add raw logs or secret-bearing config data to the output.
        entity_html = "".join(f"<li><code>{e(name)}</code></li>" for name in finding.entities[:80])
        more = (f"<li>… and {len(finding.entities)-80} more</li>"
                if len(finding.entities) > 80 else "")
        entities = f'<details><summary>View affected entities ({len(finding.entities)})</summary><ul>{entity_html}{more}</ul></details>' if finding.entities else ""
        cards.append(f'''<article class="finding" data-level="{e(finding.severity)}">
            <div class="finding-top"><span class="pill {e(finding.severity)}">{e(finding.severity).upper()}</span>
            <span class="code">{e(finding.code)}</span></div>
            <h3>{e(finding.title)}</h3><p>{e(finding.detail)}</p>
            <div class="action"><b>Recommended next step</b><p>{e(finding.action)}</p></div>{entities}</article>''')
    finding_html = "\n".join(cards) or '<p class="empty">✓ No issues found by the enabled checks.</p>'
    notes = "".join(f"<li>{e(note)}</li>" for note in report.observations)
    exported = json.dumps(report.as_dict(), ensure_ascii=False).replace("<", "\\u003c")
    # JSON is embedded as inert application/json; escape '<' above prevents closing the tag.
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>HA Doctor — Diagnostics</title><style>
:root{{--bg:#090e18;--panel:#141c2b;--text:#eaf2ff;--muted:#a5b1c4;--stroke:#29354a;--teal:#47e1c0;--warn:#f8bc62;--bad:#ff7187}}
*{{box-sizing:border-box}}body{{margin:0;font-family:ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:radial-gradient(ellipse at 80% -20%,#1b3b50 0%,transparent 48%),var(--bg);color:var(--text)}}
main{{max-width:1060px;margin:auto;padding:54px 24px 90px}}.top{{display:flex;align-items:center;gap:14px;flex-wrap:wrap}}.logo{{display:grid;place-items:center;width:56px;height:56px;border-radius:17px;background:#123c3b;font-size:30px}}h1{{font-size:clamp(34px,6vw,54px);line-height:1.08;letter-spacing:-.055em;margin:0}}.lead{{font-size:18px;color:var(--muted);max-width:650px;line-height:1.6}}.tag{{font-size:12px;color:var(--teal);font-weight:700;letter-spacing:.12em;text-transform:uppercase}}.stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:32px 0}}.stat{{background:var(--panel);border:1px solid var(--stroke);border-radius:18px;padding:22px}}.stat span{{display:block;font-size:13px;color:var(--muted);margin-bottom:8px}}.stat strong{{font-size:35px;letter-spacing:-.06em}}.sectionhead{{display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap;margin:42px 0 19px}}h2{{font-size:25px;margin:0;letter-spacing:-.03em}}.filters{{display:flex;gap:7px;flex-wrap:wrap}}button{{background:transparent;color:var(--muted);border:1px solid var(--stroke);border-radius:100px;padding:9px 14px;cursor:pointer}}button.active,button:hover{{color:var(--bg);background:var(--teal);border-color:var(--teal)}}.findings{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}}.finding{{padding:23px;border:1px solid var(--stroke);border-radius:18px;background:var(--panel)}}.finding-top{{display:flex;align-items:center;justify-content:space-between;gap:14px}}.pill{{border-radius:99px;padding:5px 10px;font-size:10px;letter-spacing:.1em;font-weight:800}}.pill.critical{{background:#4b2030;color:#ff9fac}}.pill.warning{{background:#46351e;color:#ffd28b}}.pill.info{{background:#183c42;color:#91e7ed}}.code{{font:12px ui-monospace,monospace;color:var(--muted)}}h3{{font-size:19px;letter-spacing:-.025em;margin:19px 0 8px}}p{{line-height:1.55;color:var(--muted)}}.action{{border-top:1px solid var(--stroke);margin-top:16px;padding-top:16px}}.action b{{font-size:12px;color:var(--teal)}}.action p{{margin:7px 0}}details{{margin-top:17px;border-top:1px solid var(--stroke);padding-top:14px}}summary{{cursor:pointer;color:#c4deee;font-size:13px}}ul{{padding-left:19px}}li{{margin:7px 0;color:var(--muted);overflow-wrap:anywhere}}code{{font:12px ui-monospace,monospace}}.foot{{margin-top:42px;color:var(--muted);border-top:1px solid var(--stroke);padding-top:24px}}.empty{{padding:24px;color:var(--teal);background:var(--panel);border-radius:16px}}.minor{{font-size:12px;color:var(--muted)}}[hidden]{{display:none!important}}
@media(max-width:740px){{.stats{{grid-template-columns:repeat(2,1fr)}}.findings{{grid-template-columns:1fr}}main{{padding:30px 16px 70px}}}}
</style></head><body><main>
<header><div class="top"><div class="logo" aria-hidden="true">🩺</div><div><div class="tag">Local-only · Read-only · Open source</div><h1>HA Doctor</h1></div></div>
<p class="lead">Find the broken bits of your Home Assistant setup. Correlated outages, unavailable entities, stale reports and meaningful log patterns — all in one place.</p>
<p class="minor">Generated {e(report.generated_at)} · Home Assistant {e(report.version)} · No configuration changes performed</p></header>
<section class="stats">{badges}</section>
<section><div class="sectionhead"><h2>Diagnostic findings</h2><div class="filters" role="group" aria-label="Severity filter">
<button type="button" class="active" data-filter="all">All</button><button type="button" data-filter="critical">Critical</button><button type="button" data-filter="warning">Warning</button><button type="button" data-filter="info">Info</button></div></div>
<div class="findings">{finding_html}</div></section>
<section class="foot"><h2>Diagnostic notes</h2><ul>{notes}</ul><p class="minor">This report is stored on your machine. Entity IDs may reveal private details: review before sharing. HA Doctor never uploads the report.</p></section>
<script type="application/json" id="report-data">{exported}</script>
<script>document.querySelectorAll('[data-filter]').forEach(btn=>btn.addEventListener('click',()=>{{document.querySelectorAll('[data-filter]').forEach(b=>b.classList.toggle('active',b===btn));document.querySelectorAll('.finding').forEach(card=>card.hidden=btn.dataset.filter!=='all'&&card.dataset.level!==btn.dataset.filter);}}));</script>
</main></body></html>'''
