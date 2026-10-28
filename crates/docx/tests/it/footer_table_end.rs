//! A footer may end in a table: saving must not add a line that moves it upward.
use std::sync::Arc;
use wordcraft_doc::{Block, Document, Paragraph, PartKind, Table, para_block};

fn roundtrip(doc: &Document) -> Document {
    wordcraft_docx::read(&wordcraft_docx::write(doc).unwrap()).unwrap()
}

#[test]
fn table_only_footer_does_not_gain_a_paragraph_on_save() {
    let mut doc = Document::from_text("Synthetic body");
    let id = doc.add_part(PartKind::Footer, vec![Arc::new(Block::Table(Table::new(2, 2, 300.0)))]);
    doc.last_section.footers.default = Some(id);
    for _ in 0..2 {
        doc = roundtrip(&doc);
        let part = &doc.parts[&doc.last_section.footers.default.unwrap()];
        assert_eq!(part.blocks.len(), 1, "an added empty paragraph changes footer height and placement");
        assert!(matches!(&*part.blocks[0], Block::Table(_)));
    }
}

#[test]
fn explicit_footer_paragraph_after_a_table_is_preserved() {
    let mut doc = Document::from_text("Synthetic body");
    let mut ending = Paragraph::new();
    ending.props.space_after = Some(7.0);
    let id = doc.add_part(PartKind::Footer, vec![Arc::new(Block::Table(Table::new(1, 1, 300.0))), para_block(ending)]);
    doc.last_section.footers.default = Some(id);
    let read = roundtrip(&doc);
    let part = &read.parts[&read.last_section.footers.default.unwrap()];
    assert_eq!(part.blocks.len(), 2);
    assert_eq!(part.blocks[1].as_para().unwrap().props.space_after, Some(7.0));
}

#[test]
fn an_empty_footer_still_gets_a_paragraph() {
    let mut doc = Document::from_text("Synthetic body");
    let id = doc.add_part(PartKind::Footer, vec![]);
    doc.last_section.footers.default = Some(id);
    let read = roundtrip(&doc);
    let part = &read.parts[&read.last_section.footers.default.unwrap()];
    assert_eq!(part.blocks.len(), 1);
    assert!(part.blocks[0].as_para().is_some());
}

#[test]
fn table_cells_still_end_in_a_paragraph() {
    let mut doc = Document::from_text("Synthetic body");
    let mut outer = Table::new(1, 1, 300.0);
    outer.rows[0].cells[0].blocks = vec![Arc::new(Block::Table(Table::new(1, 1, 200.0)))];
    let id = doc.add_part(PartKind::Footer, vec![Arc::new(Block::Table(outer))]);
    doc.last_section.footers.default = Some(id);
    let read = roundtrip(&doc);
    let part = &read.parts[&read.last_section.footers.default.unwrap()];
    let Block::Table(table) = &*part.blocks[0] else { panic!("table") };
    assert_eq!(table.rows[0].cells[0].blocks.len(), 2);
    assert!(table.rows[0].cells[0].blocks.last().unwrap().as_para().is_some());
}
