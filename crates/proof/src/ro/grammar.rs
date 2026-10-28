//! Romanian grammar and punctuation checks: cheap, rule-based and tuned to stay quiet when
//! unsure (a missed mistake costs less than a wrong mark on correct text). Messages are in
//! Romanian.
//!
//! - **Repeated word** (`la la`), except words Romanian doubles on purpose (`încet încet`,
//!   `da da`, interjections).
//! - **Space before punctuation** (`bine ,`) and **double spaces**; emoticons (` :)`) and
//!   ellipses are left alone.
//! - **Capital letter at the start of a sentence**, knowing Romanian abbreviations (`etc.`,
//!   `dl.`, `prof.`, `nr.`, `str.`), initials, ordinal numbers and ellipses, and the low opening
//!   quote `„`.
//! - **Doubled punctuation** (`,,`, `..`, `;;`).
//!
//! Context-dependent changes (`nici un`, punctuation before `ci`/`dar`) are left alone:
//! without grammatical analysis they misclassify valid correlative wording, nouns and office
//! abbreviations such as `CI`. This module does not claim full Romanian grammar checking.
//!
//! No English rule (such as `a`/`an`) applies to Romanian text.

use crate::{Issue, IssueKind, ProofLang, words};

/// Words Romanian repeats on purpose: emphatic doubling, interjections, onomatopoeia.
const ALLOWED_REPEATS: &[&str] = &[
    "da", "nu", "încet", "repede", "bine", "mereu", "tare", "hai", "ha", "he", "hi", "ah", "oh", "ei", "aoleu", "vai", "na", "uite", "gata", "pas",
    "puțin", "câte", "unul", "una",
];

/// Abbreviations written with a final period after which a sentence goes on in lower case
/// (lower case, without the period).
const ABBREVIATIONS: &[&str] = &[
    "etc", "dl", "dna", "dra", "dlui", "dnei", "dnul", "dvs", "dv", "prof", "conf", "lect", "asist", "dr", "ing", "ec", "av", "arh", "acad", "pr",
    "sf", "st", "gen", "col", "lt", "mr", "cpt", "sg", "nr", "pag", "pg", "p", "pp", "vol", "cap", "art", "alin", "lit", "pct", "par", "fig", "tab",
    "str", "bd", "bdul", "bl", "sc", "ap", "et", "jud", "mun", "or", "com", "sat", "loc", "tel", "fax", "ex", "cf", "cca", "aprox", "max", "min",
    "sec", "mil", "mld", "lei", "ian", "feb", "febr", "mar", "apr", "iun", "iul", "aug", "sept", "oct", "nov", "dec", "lun", "mie", "joi", "vin",
    "sâm", "dum", "ed", "red", "trad", "coord", "op", "cit", "ibid", "id", "v", "vs", "obs", "n", "s", "a", "î", "d", "hr",
];

fn issue(start: usize, end: usize, message: String, suggestions: Vec<String>) -> Issue {
    Issue { start, end, kind: IssueKind::Grammar, message, suggestions, lang: ProofLang::Ro }
}

/// Is `prev`, before a period, an abbreviation, an initial, a number or a Roman numeral (after
/// which a lower-case word doesn't start a sentence)?
fn abbreviation_or_number(prev: &str) -> bool {
    prev.chars().count() <= 1
        || prev.chars().any(|c| c.is_ascii_digit())
        || (prev.chars().all(|c| matches!(c, 'I' | 'V' | 'X' | 'L' | 'C' | 'D' | 'M')))
        || ABBREVIATIONS.contains(&super::comma_below(&prev.to_lowercase()).as_str())
}

/// Does the gap between two words end a sentence: a `.`, `!` or `?` (not an ellipsis, not after
/// an abbreviation), then space, with nothing but quotes and brackets around?
fn ends_sentence(gap: &str, prev: &str) -> bool {
    let t = gap.trim_start_matches(['"', '”', '’', '\'', ')', '»', ']', '\u{1}']);
    let Some(end) = t.chars().next() else { return false };
    if !matches!(end, '.' | '!' | '?') || t.starts_with("..") {
        return false;
    }
    if end == '.' && abbreviation_or_number(prev) {
        return false;
    }
    let rest = t.trim_start_matches(['.', '!', '?']).trim_start_matches(['"', '”', '’', '\'', ')', '»', ']']);
    rest.starts_with(char::is_whitespace) && rest.trim_start().chars().all(|c| matches!(c, '"' | '„' | '“' | '«' | '(' | '[' | '\'' | '—' | '–'))
}

fn repeated_words(text: &str, ws: &[(usize, usize)], v: &mut Vec<Issue>) {
    for pair in ws.windows(2) {
        let [(a0, b0), (a1, b1)] = pair else { continue };
        let (Some(w0), Some(w1), Some(gap)) = (text.get(*a0..*b0), text.get(*a1..*b1), text.get(*b0..*a1)) else { continue };
        if !gap.is_empty()
            && gap.chars().all(char::is_whitespace)
            && w0.chars().all(char::is_alphabetic)
            && super::comma_below(&w0.to_lowercase()) == super::comma_below(&w1.to_lowercase())
            && !ALLOWED_REPEATS.contains(&super::comma_below(&w0.to_lowercase()).as_str())
        {
            v.push(issue(*a0, *b1, format!("Cuvânt repetat: „{w1}”"), vec![w0.to_string()]));
        }
    }
}

fn spaces(text: &str, v: &mut Vec<Issue>) {
    for (i, c) in text.char_indices() {
        if c != ' ' {
            continue;
        }
        let rest = text.get(i + 1..).unwrap_or("");
        let mut it = rest.chars();
        let Some(p) = it.next() else { continue };
        let after = it.next();
        let flag = match p {
            ',' => true,
            // `;)` and `;-)` are emoticons.
            ';' => !matches!(after, Some(')' | '(' | '-' | 'P' | 'D')),
            // ` ...` is an ellipsis, ` .5` a number.
            '.' => !matches!(after, Some('.')) && !after.is_some_and(|a| a.is_ascii_digit()),
            // ` :)`, ` :-)`, ` :D` and similar are emoticons; ` ?!` is still a stray space.
            ':' | '!' | '?' => after.is_none_or(|a| a.is_whitespace() || matches!(a, '"' | '”' | '’' | '!' | '?')),
            _ => false,
        };
        if flag {
            v.push(issue(i, i + 1 + p.len_utf8(), "Spațiu înaintea semnului de punctuație".into(), vec![p.to_string()]));
        }
    }
    for (i, _) in text.match_indices("  ") {
        if i > 0 && text.get(..i).is_some_and(|t| t.ends_with(' ')) {
            continue;
        }
        v.push(issue(i, i + 2, "Spațiu dublu".into(), vec![" ".into()]));
    }
}

fn sentence_capitals(text: &str, ws: &[(usize, usize)], capital_first: bool, v: &mut Vec<Issue>) {
    let mut after_end = capital_first;
    for (k, (a, b)) in ws.iter().enumerate() {
        let Some(w) = text.get(*a..*b) else { continue };
        if after_end && w.chars().next().is_some_and(char::is_lowercase) && w.chars().all(char::is_alphabetic) {
            let fixed: String = w.chars().next().map(|f| f.to_uppercase().chain(w.chars().skip(1)).collect()).unwrap_or_default();
            v.push(issue(*a, *b, "Majusculă la început de propoziție".into(), vec![fixed]));
        }
        // Only the gap up to the next word decides (`Salut. apoi`: `. ` ends the sentence).
        let next = ws.get(k + 1).map_or(text.len(), |n| n.0);
        after_end = ends_sentence(text.get(*b..next).unwrap_or(""), w);
    }
}

fn doubled_punctuation(text: &str, v: &mut Vec<Issue>) {
    for pat in [",,", "..", ";;", "::", "??", "!!"] {
        for (i, _) in text.match_indices(pat) {
            if pat == ".." && text.get(i + 2..).is_some_and(|r| r.starts_with('.')) {
                continue; // ellipsis
            }
            if pat == ".." && text.get(..i).is_some_and(|t| t.ends_with('.')) {
                continue; // the end of an ellipsis
            }
            v.push(issue(i, i + pat.len(), "Punctuație dublă".into(), vec![pat[..1].into()]));
        }
    }
}

/// Grammar issues in a paragraph of Romanian text, in order.
pub fn check(text: &str) -> Vec<Issue> {
    check_with(text, true)
}

/// [`check`] where `capital_first` says whether the text's first word must start a sentence with
/// a capital (false for a list item, which may be a fragment).
pub fn check_with(text: &str, capital_first: bool) -> Vec<Issue> {
    let ws: Vec<(usize, usize)> = words(text);
    let mut v = Vec::new();
    repeated_words(text, &ws, &mut v);
    spaces(text, &mut v);
    sentence_capitals(text, &ws, capital_first, &mut v);
    doubled_punctuation(text, &mut v);
    v.sort_by_key(|i| (i.start, i.end));
    v
}

#[cfg(test)]
mod tests {
    /// Office abbreviations and contextual wording must not receive speculative replacements.
    #[test]
    fn office_wording_does_not_receive_contextual_grammar_guesses() {
        for text in ["Anexăm copie CI pentru verificare.", "Nu este nici un calculator, nici un telefon.", "Bunul primit este dar, nu împrumut."] {
            assert!(check(text).is_empty(), "{text}: {:?}", check(text));
        }
    }

    use super::*;

    fn messages(t: &str) -> Vec<String> {
        check(t).into_iter().map(|i| i.message).collect()
    }

    #[test]
    fn romanian_grammar_flags() {
        let t = "acesta acesta este un test ,  făcut prost.. Vezi dl. Popescu";
        let v = check(t);
        let msgs: Vec<&str> = v.iter().map(|i| i.message.as_str()).collect();
        assert!(msgs.contains(&"Cuvânt repetat: „acesta”"), "{msgs:?}");
        assert!(msgs.contains(&"Spațiu înaintea semnului de punctuație"), "{msgs:?}");
        assert!(msgs.contains(&"Spațiu dublu"), "{msgs:?}");
        assert!(msgs.contains(&"Punctuație dublă"), "{msgs:?}");
        assert!(msgs.contains(&"Majusculă la început de propoziție"), "{msgs:?}");
        assert!(v.iter().all(|i| i.lang == ProofLang::Ro), "{v:?}");
    }

    #[test]
    fn a_lower_case_second_sentence_is_flagged() {
        let v = check("Salut. apoi am plecat.");
        assert_eq!(v.len(), 1, "{v:?}");
        assert_eq!((v[0].message.as_str(), v[0].suggestions[0].as_str()), ("Majusculă la început de propoziție", "Apoi"));
        assert_eq!(&"Salut. apoi am plecat."[v[0].start..v[0].end], "apoi");
        // After a quotation mark or bracket too; never after an abbreviation or an ellipsis.
        assert_eq!(messages("A venit.” apoi a plecat."), ["Majusculă la început de propoziție"]);
        assert!(check("Merge cu dl. Popescu... apoi pleacă.").is_empty());
    }

    #[test]
    fn romanian_grammar_stays_quiet() {
        for t in [
            "Merg la București. Dl. Popescu e deja acolo... încet încet!",
            "Da da, bine bine :)",
            "A sosit la ora 5. pe str. Lungă, nr. 3, etc. și apoi a plecat.",
            "El a spus: „Vin mâine.” Apoi a tăcut.",
            "Nu am nicio carte și niciun caiet.",
            "Nu vreau nici unul, nici altul.",
            "Nu vine azi, ci mâine. Am vrut, dar n-am putut.",
            "Dar cine a venit? A primit un dar frumos.",
            "Cartea a fost un adevărat dar de la el.",
        ] {
            assert!(check(t).is_empty(), "{t}: {:?}", check(t));
        }
    }

    #[test]
    fn cedilla_spellings_are_read_too() {
        // `şi` with a cedilla is the same word as `și`.
        assert!(check("Merg şi eu.").is_empty());
        assert!(check("Nu am nici un leu.").is_empty(), "context-dependent wording stays unchanged");
        // Repeats are compared with the cedilla read as comma-below: `şcoală școală` repeats,
        // and the allowed `puțin puțin` is allowed in either spelling.
        assert_eq!(messages("Merg la şcoală școală."), ["Cuvânt repetat: „școală”"]);
        assert!(check("Mai stai puţin puţin.").is_empty());
    }
}
