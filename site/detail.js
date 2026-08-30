/* Shared by BOTH pages — docs/index.html and docs/simple/index.html.
   Inlined at build time by scripts/build_site.py rather than
   loaded as a file, because each page is a single self-contained
   document served by GitHub Pages.

   It lives here so the two pages CANNOT drift: the expanded panel, the
   gate wording and the five-year record are one implementation. The
   simple page exists for a reader who does not want the detail up
   front — not for a reader who should be shown less of it.
*/
// Plain English for the gate names. The backend labels are precise but
// assume finance vocabulary; these say the same thing to a reader who
// does not have it.
// Stage 3's label, shortened for the table only. The full wording lives
// in the expanded panel — a cell cannot hold "cheaper than usual, profit
// falling" without squeezing every other column.
const READ_SHORT = {
  "cheaper than usual":    "cheaper",
  "priced about as usual": "as usual",
  "pricier than usual":    "pricier",
  "profit holding up":     "",
  "not enough history":    "",
};
function readCell(r){
  if(!r.s3) return "";
  const falling = /profit falling/.test(r.s3.l);
  const base = r.s3.l.replace(/, profit falling$/, "");
  const short = READ_SHORT[base] ?? "";
  // Form, not colour. The funnel refuses to say whether a fall is good
  // or bad, so "profit falling" is stated as a fact, never flagged red.
  // "no earnings history" and "—" are different statements: the first
  // says gate 1 could not be measured, the second would say nothing was
  // found at all. 14 of 260 companies have EPS tags that stop years ago
  // (Monster's end in 2010), and for those we still know whether profit
  // is holding — so the cell must report what WAS established.
  // Detect gate 1's absence from the DATA, not the label. A first
  // attempt tested the label against READ_SHORT, but "profit holding up"
  // IS in that table — so the exact case this is for, a company with no
  // yield history whose profit is fine, fell through and still showed a
  // bare dash.
  const value = short ? `<span class="read">${short}</span>`
              : !r.s3.y ? `<span class="read faintly">no earnings history</span>`
              : "";
  const note  = falling ? `<span class="read falling">profit falling</span>` : "";
  return (value || note) ? value + note : "—";
}

// The four ways a gate says "there was nothing here to measure". Read as
// malfunctions by anyone who does not know the vocabulary, and §3.5 is
// explicit that CANNOT ASSESS is never the same as REJECTED — so neither
// the label nor the detail may imply a failure.
const UNMEASURED=/^(insufficient history|no revenue tag match|no usable revenue series|no interest or equity tag|no cash-flow tag|no profit tag)$/;
const NEUTRAL={
  "Sustained profit":"Profit record",
  "Return on capital":"Returns on capital",
  "Cumulative 5y FCF":"Spare cash",
  "Debt serviceable":"Debt",
  "Op margin durable":"Margins",
  "Revenue durability":"Sales growth",
};
const GATE_LABEL={
  "Sustained profit":"Profitable every year",
  "Return on capital":"Earns well on its assets",
  "Cumulative 5y FCF":"Generates spare cash",
  "Debt serviceable":"Can cover its interest",
  "Op margin durable":"Margins holding up",
};

// Rewrites the backend's terse detail strings into sentences. Every
// number is carried through unchanged — only the words around them
// differ. If a string does not match its expected shape the raw version
// is shown rather than a guess, so this can never invent a figure.
function plain(gate, d){
  let m;
  if(gate==="Sustained profit" &&
     (m=d.match(/profit negative (\d+)\/(\d+)y \(allowed (\d+)\)[^]*?net income positive (\d+)\/(\d+)/))){
    const [,neg,yrs,,niGood,niYrs]=m;
    return `Made an operating profit in ${yrs-neg} of the last ${yrs} years, `
         + `and a bottom-line profit in ${niGood} of ${niYrs}.`;
  }
  if(gate==="Return on capital"){
    if((m=d.match(/return on (assets|equity) median ([\d.]+)% vs (\d+)% bar[^]*?latest ([\d.]+)%/))){
      const [,kind,med,bar,latest]=m;
      const what = kind==="assets" ? "everything it owns" : "shareholders' money";
      return `Earns ${med}% a year on ${what}, against a ${bar}% bar. `
           + `Most recent year: ${latest}%.`;
    }
  }
  if(gate==="Cumulative 5y FCF" && (m=d.match(/\$([+-]?)([\d.]+)B over (\d+)y/))){
    return m[1] === "-"
      ? `Spent $${m[2]}B more than it brought in over ${m[3]} years, after paying `
      + `for the equipment and buildings it needs.`
      : `Threw off $${m[2]}B of spare cash over ${m[3]} years, after paying `
      + `for the equipment and buildings it needs.`;
  }
  if(gate==="Debt serviceable"){
    if((m=d.match(/interest coverage ([\d.]+)x vs ([\d.]+)x bar/)))
      return `Profits cover its interest bill ${m[1]} times over. `
           + `It needs to cover it at least ${m[2]} times.`;
    if((m=d.match(/equity\/assets ([\d.]+)% vs (\d+)% bar/)))
      return `Owns ${m[1]}% of its assets outright rather than owing them, `
           + `against a ${m[2]}% bar.`;
  }
  if(gate==="Op margin durable" &&
     (m=d.match(/latest (-?[\d.]+)% is (-?\d+)% of 3y avg (-?[\d.]+)% \((\d+)% bar\)/))){
    const [,latest,pct,avg,bar]=m;
    return Number(latest) < 0
      ? `Lost ${Math.abs(latest)} cents per dollar of sales last year, against a `
      + `${avg}% three-year average — it must stay above ${bar}% of that average.`
      : `Keeps ${latest} cents of profit per dollar of sales. That is ${pct}% `
      + `of its ${avg}% three-year average — it must stay above ${bar}%.`;
  }
  // Gate 6 had no case here at all, so every company showed it raw:
  // "revenue grew 10.6% a year over 5y (2021-2025)".
  if(gate==="Revenue durability"){
    if((m=d.match(/revenue grew ([\d.-]+)% a year over (\d+)y \(\d+-(\d+)\)/))){
      const words={2:"two",3:"three",4:"four",5:"five"}[m[2]] || m[2];
      return `Sales grew ${m[1]}% a year over the ${words} years to ${m[3]}.`;
    }
    if((m=d.match(/shrinking (-?[\d.]+)% a year[^]*?latest revenue is (\d+)% of its own 3y/)))
      return `Sales are shrinking ${m[1].replace("-","")}% a year, but last year `
           + `still came in at ${m[2]}% of its own three-year average.`;
  }
  // A company that reports cash in but never breaks out what it spent on
  // equipment: we can say what came in, but not what was left over, and
  // the page must not imply we know the second.
  if(gate==="Cumulative 5y FCF" && (m=d.match(/\$\+?([\d.]+)B operating cash \(no capex tag\)/)))
    return `Brought in $${m[1]}B of cash from trading. It does not report what it `
         + `spent on equipment and buildings, so what was left over cannot be worked out.`;
  // "utility track" and "capex" are our vocabulary, not a reader's.
  if(gate==="Cumulative 5y FCF" &&
     (m=d.match(/operating cash flow positive (\d+)\/(\d+)y/)))
    return `Brought in cash in ${m[1]} of ${m[2]} years. For utilities the spending `
         + `on power lines and plants is left out, because building them is the business.`;

  // The "nothing to measure" family. Stated as an absence of a figure,
  // never as a fault — see UNMEASURED above.
  if(d==="insufficient history")
    return "Too few years of filings to judge this one.";
  if(d==="no revenue tag match" || d==="no usable revenue series")
    return "This company does not report the sales figure this check needs.";
  if(d==="no cash-flow tag")
    return "This company does not report the cash-flow figures this check needs.";
  if(d==="no profit tag")
    return "This company does not report the profit figure this check needs.";
  if(d==="no interest or equity tag")
    return "This company reports neither its interest bill nor its equity, so there "
         + "is nothing to measure its debt against.";

  return d;   // unrecognised shape: show it as filed rather than guess
}

// "2026-02-28" is parsed by Date() as UTC midnight and then rendered in
// the READER'S timezone, so anyone west of Greenwich saw every date a day
// early — fiscal year ends included, since this page shipped. Appending a
// time forces local parsing. Every date on the page goes through here.
function onDate(iso){ return new Date(iso + "T00:00:00"); }
const longDate = iso => onDate(iso).toLocaleDateString("en-GB",
  {day:"numeric", month:"long", year:"numeric"});

// "over three years" is not checkable without saying WHICH three.
function yrs(s3, k){
  const y = s3.yy && s3.yy[k];
  return y ? ` over ${y[0]}\u2013${y[1]}` : "";
}

// "22.4% then -13.0%" made the reader work out which quarter was which
// and what the sign meant. One sentence per quarter, with the direction
// as a word and the date spelled out.
function qtr(s3, i){
  const v = s3.q[i], end = s3.qq && s3.qq[i];
  const when = end ? `In the quarter to ${longDate(end)}`
                   : (i === 1 ? "In the latest quarter" : "In the quarter before that");
  const dir = v < 0 ? "lower" : "higher";
  return `${when}, operating profit was <b>${Math.abs(v).toFixed(1)}%</b> `
       + `${dir} year on year.`;
}

function detail(r){
  const a200=(r.p/(1-r.m2/100)), a50=(r.p/(1-r.m5/100));
  const gates=r.gt.map(g=>{
    const risk = r.ar && r.ar.startsWith(g[0]);
    const raw  = g[0].replace(/^\d+\s+/, "");
    // Gate 4 is TWO tests. Where interest expense is reported it checks
    // whether profit covers the interest; where it is not, it falls back
    // to how much of the balance sheet the company owns outright, which
    // is a leverage test. One label cannot honestly describe both.
    // Gates 4 and 6 are each TWO tests, so neither can carry one label.
    // Gate 4: interest coverage, or the equity/assets fallback.
    // Gate 6: grew across the window, or held its own 3-year average.
    // "Still growing" beside a detail reading "shrinking 9.5% a year"
    // is the same defect "Debt under control" had.
    // A label ASSERTS. Where the check could not run at all, every one of
    // these asserts something that did not happen — "Profitable every
    // year" above "insufficient history", "Can cover its interest" above
    // "no interest or equity tag". Those drop to a neutral topic, which
    // claims nothing. Same defect as "Still growing" over "shrinking",
    // one step further back.
    // A label may only ASSERT where the check actually ran AND the
    // company cleared it. Two cases drop to the neutral topic instead:
    // the check could not run (fixed in v2.19), and — this — the check
    // ran and FAILED. "Margins holding up" sat above "Lost 118.1 cents
    // per dollar of sales" on 243 of 470 companies, and once the
    // collapsed head began summarising the same gates as "falls short
    // on margins", one panel asserted both.
    const clears = g[1] === "pass" || g[1] === "near-pass";
    let label = clears ? (GATE_LABEL[raw] || raw) : (NEUTRAL[raw] || raw);
    if (clears && raw === "Debt serviceable")
      label = /interest coverage/.test(g[2]) ? "Can cover its interest"
                                             : "Not overloaded with debt";
    if (clears && raw === "Revenue durability")
      label = /grew/.test(g[2]) ? "Still growing" : "Revenue holding up";
    return `<div class="gate${risk?" risk":""}">
      <div class="g">${label}</div>
      <div class="d">${plain(raw, g[2])}</div>
      <div class="v">${risk?"closest":(g[1]||"n/a")}</div>
    </div>`;}).join("");

  const months=Math.round((onDate("{{TODAY}}")-onDate(r.pe))/2629800000);
  const ended=onDate(r.pe).toLocaleDateString("en-GB",
    {day:"numeric",month:"long",year:"numeric"});

  // where today's price sits between the 52-week extremes
  const span = r.hi - r.lo;
  const pos  = span > 0 ? Math.max(0, Math.min(100, (r.p - r.lo) / span * 100)) : 0;
  // keep the floating label inside the track at either extreme
  const shift = pos <= 10 ? "0" : pos >= 90 ? "-100%" : "-50%";
  // Each distance is measured against the endpoint it refers to, so the
  // two are constructed the same way. Measuring both from today's price
  // would give the same position two unrelated-looking numbers.
  // Deliberately NOT called "upside": the 52-week high is the highest
  // price in a year, not a target, and "upside" would claim it is one.
  const upFromLow    = ((r.p - r.lo) / r.lo  * 100).toFixed(1);
  const downFromHigh = ((r.hi - r.p) / r.hi * 100).toFixed(1);

  // The heading has to tell the truth for whatever was looked up. On the
  // ranked list every row qualified; the lookup can return a company that
  // failed, or one with too little history to judge.
  const H = {
    "PASS":"Why it is on the watchlist",
    "BORDERLINE":"Why it is on the watchlist — and what it barely cleared",
    "REJECTED":"Why it did not qualify",
    "CANNOT ASSESS":"Not enough filing history to judge",
  }[r.tier] || "Not assessed";

  // A REIT note stood here and was unreachable: REITs are excluded from
  // the page entirely (§6 principle 7), so ROWS holds 470 companies and
  // not one carries a REIT tier. The explanation a reader needs already
  // sits in the page's notes, where it can be found without clicking a
  // company that is not there.

  const scaleInner = (r.lo == null || r.hi == null || r.hi <= r.lo) ? "" :
   `
      <div class="scale">
        <div class="track">
          <span class="tick lo"></span><span class="tick hi"></span>
          <span class="now" style="left:${pos}%"></span>
          <span class="nowlab" style="left:${pos}%;transform:translateX(${shift})"
            >$${r.p.toFixed(2)}<small>(${upFromLow}%, ${downFromHigh}%)<sup>*</sup></small></span>
          <span class="endlab lo">$${r.lo.toFixed(2)}</span>
          <span class="endlab hi">$${r.hi.toFixed(2)}</span>
        </div>
      </div>
      <p class="footnote"><sup>*</sup> above the 52-week low, and below
        the 52-week high</p>`;

  // The years behind the statistics each gate reports. A median hides
  // whether 5% is steady, recovering or collapsing.
  // The record is split across the stage sections rather than sitting in
  // one block: a trend belongs beside the question it is evidence for.
  const recFor = stage => {
    const g = (r.sr && r.sr.groups || []).find(x => x.stage === stage);
    if (!g) return "";
    return `<div class="rec"><table class="rec-t">
        <thead><tr><th class="lbl"></th>
          ${g.years.map(y => `<th>${y}</th>`).join("")}
          <th class="bar">${g.barhead || "at least"}</th></tr></thead>
        <tbody>${g.rows.map(([label, vals, bar]) => `<tr>
            <td class="lbl">${label}</td>
            ${vals.map(v => `<td>${v === null ? "—" : v.toFixed(1)}</td>`).join("")}
            <td class="bar">${bar}</td></tr>`).join("")}</tbody>
      </table></div>`;
  };

  // Stage 3 ANNOTATES; it never reorders or scores. The AGE of the
  // quarterly evidence is shown because a company just past its fiscal
  // year end files no Q4 10-Q, so a 6-month-old quarter is honest rather
  // than neglectful — the reader has to see that, not trust a bare label.
  const s3 = r.s3;
  const s3Gates = !s3 ? "" : `
      ${!s3.y ? "" : `<div class="gate">
        <div class="g">Cheaper than usual?</div>
        <div class="d">Every dollar you pay today buys
          <b>${s3.y[0].toFixed(2)}%</b> a year of earnings. Its own history
          bought <b>${s3.y[1].toFixed(2)}%</b>${yrs(s3,"3")} and
          <b>${s3.y[2].toFixed(2)}%</b>${yrs(s3,"5")} —
          so a dollar buys ${s3.y[0] > Math.max(s3.y[1],s3.y[2]) ? "MORE"
            : s3.y[0] <= Math.min(s3.y[1],s3.y[2]) ? "LESS" : "about as much"}
          earnings than usual.</div>
        <div class="v"></div></div>`}
      ${!s3.q ? "" : `<div class="gate">
        <div class="g">Profit still holding?</div>
        <div class="d">${qtr(s3, 1)} ${qtr(s3, 0)}
          <span class="asof">Each compared with the SAME quarter a year
            earlier, so seasonal ups and downs cancel out. Latest filed
            ${s3.qa} days ago.</span></div>
        <div class="v"></div></div>`}`;



  // ONE CARD PER STAGE, in funnel order, each headed by the question that
  // stage asks. Before this, Stage 2's two cards sat at opposite ends of
  // the panel with four unrelated cards between them, and only the
  // five-year record named its stages at all.
  // A stage is a SECTION containing separate boxes, not one large box.
  // Gates, the historical record and the currency note are different
  // kinds of thing and each now has its own frame.
  /* Each stage collapses to its ANSWER. Opening a company used to dump
     six gates, a five-year grid, a price scale and Stage 3 at once —
     everything at the same weight, so nothing read as the answer. The
     summary line carries the finding; the working is one click further.
     Native <details>, so it is keyboard-reachable with no script. */
  // A gate the filings could not answer carries grade null. It is not a
  // gate that failed, so it is never folded into "passes N of M" — it is
  // counted and named apart. `ar` is "gate|detail", and that detail is
  // backend wording: split it, and take the neutral TOPIC of the gate,
  // never the assertion label, which would claim a result of its own.
  const topic = name => {
    const raw = String(name).replace(/^\d+\s+/, "");
    return (NEUTRAL[raw] || raw).toLowerCase();
  };
  const gt     = r.gt || [];
  const totN   = gt.length;
  const unmN   = gt.filter(g => g[1] == null).length;
  const passN  = gt.filter(g => g[1] === "pass" || g[1] === "near-pass").length;
  const failed = gt.filter(g => g[1] === "fail" || g[1] === "near-fail");
  const readN  = totN - unmN;
  let sum1 = "";
  if (totN){
    if (passN === readN){
      // readN === 0 is the trap: "passes all 0 checks" reads as a pass
      // where NOTHING was measured. Say what happened instead.
      sum1 = readN === 0
        ? `None of the ${totN === 6 ? "six" : totN} checks could be read`
        : unmN ? `Passes the ${readN} checks that could be read — ${unmN} could not be`
               : `Passes all ${readN === 6 ? "six" : readN} checks`;
      // grazing a gate it still passes: the one worth knowing about
      if (r.ar) sum1 += ` — closest to failing: ${topic(r.ar.split("|")[0])}`;
    } else {
      sum1 = `Passes ${passN} of ${readN}`;
      if (failed.length) sum1 += ` — falls short on ${failed.map(g => topic(g[0])).join(", ")}`;
      if (unmN) sum1 += `${failed.length ? ";" : " —"} ${unmN} could not be read`;
    }
  }
  const sum2 = r.b == null ? "" :
      `${r.b.toFixed(1)}% below its usual price${r.q3b ? ` · ${r.q3b}` : ""}`;
  const sum3 = !s3 ? "" : s3.l;

  const head = (q, why, sum) => `<summary class="stage-sum">
      <span class="stage-q">${q}</span>
      <span class="stage-why">${why}</span>
      ${sum ? `<span class="stage-ans">${sum}</span>` : ""}
    </summary>`;

  const stage1 = (gates || recFor(1)) ? `<details class="stage">
      ${head("Would I ever want to own this?",
             "Six checks on five years of audited accounts — profit, returns, cash, debt, margins, revenue.",
             sum1)}
      ${!gates ? "" : `<div class="card">
        <p class="gate-cap">${H}</p>
        ${gates}
      </div>`}
      ${!recFor(1) ? "" : `<div class="card">${recFor(1)}</div>`}
      ${!r.pe ? "" : `<div class="card stale-card"><p class="stale">These
        gates read the last annual report, covering the year to
        <b>${ended}</b> — roughly <b>${months} months</b> of trading ago.
        Nothing since is reflected here.</p></div>`}
    </details>` : "";

  const stage2 = r.b == null ? "" : `<details class="stage">
      ${head("Has it moved from its own normal?",
             "How far today's price sits below the average this company has traded at, and where it sits in its own 3-year range.",
             sum2)}
      ${!scaleInner ? "" : `<div class="card">${scaleInner}</div>`}
      <div class="card"><div class="calc">
        today <b>$${r.p.toFixed(2)}</b><span class="sep">·</span>average over
        50 days <b>$${a50.toFixed(2)}</b><span class="sep">·</span>over 200 days
        <b>$${a200.toFixed(2)}</b><br>
        below normal = 0.60 × <b>${r.m2.toFixed(1)}%</b> + 0.40 ×
        <b>${r.m5.toFixed(1)}%</b> = <b>${r.b.toFixed(1)}%</b>
        ${!r.q3l ? "" : `<br>${r.q3l}`}
      </div></div>
    </details>`;

  const stage3 = !s3 ? "" : `<details class="stage">
      ${head("Opportunity, or warning?",
             "Whether today's price is cheaper than this company's own earnings have historically cost, and whether profit is still holding up.",
             sum3)}
      <div class="card">
        ${s3Gates}
      </div>
      ${!recFor(3) ? "" : `<div class="card">${recFor(3)}</div>`}
      <div class="card stale-card"><p class="stale">The cheapness reading
        divides today's price by the SAME annual earnings Stage 1
        uses${r.pe ? ` — the year to <b>${ended}</b>` : ""}, so it is only
        as current as that filing. The profit reading uses the quarter
        dated above, which is newer.</p></div>
    </details>`;

  return `<div class="work">
    ${stage1}
    ${stage2}
    ${stage3}


  </div>`;
}

