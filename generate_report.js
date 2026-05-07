const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        AlignmentType, BorderStyle, WidthType, ShadingType, VerticalAlign } = require('docx');
const fs = require('fs');

const report = JSON.parse(process.argv[2]);

const border = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };

function makeRow(label, value, labelColor = "D5E8F0") {
    return new TableRow({
        children: [
            new TableCell({
                borders,
                width: { size: 2500, type: WidthType.DXA },
                shading: { fill: labelColor, type: ShadingType.CLEAR },
                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                children: [new Paragraph({
                    children: [new TextRun({ text: label, bold: true, font: "Arial", size: 20 })]
                })]
            }),
            new TableCell({
                borders,
                width: { size: 6860, type: WidthType.DXA },
                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                children: [new Paragraph({
                    children: [new TextRun({ text: value || "-", font: "Arial", size: 20 })]
                })]
            })
        ]
    });
}

function makeSection(title, content) {
    return [
        new Paragraph({
            children: [new TextRun({ text: title, bold: true, font: "Arial", size: 22, color: "2E75B6" })],
            spacing: { before: 200, after: 100 },
            border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: "2E75B6", space: 1 } }
        }),
        new Paragraph({
            children: [new TextRun({ text: content || "-", font: "Arial", size: 20 })],
            spacing: { before: 80, after: 80 }
        })
    ];
}

const doc = new Document({
    sections: [{
        properties: {
            page: {
                size: { width: 11906, height: 16838 },
                margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
            }
        },
        children: [
            // 제목
            new Paragraph({
                alignment: AlignmentType.CENTER,
                spacing: { before: 200, after: 400 },
                children: [
                    new TextRun({
                        text: `${report['지파명'] || ''} ${report['교회명'] || ''} 봉사 활동보고`,
                        bold: true, font: "Arial", size: 32, color: "1F4E79"
                    })
                ]
            }),

            // 활동명
            new Paragraph({
                alignment: AlignmentType.CENTER,
                spacing: { after: 400 },
                children: [
                    new TextRun({
                        text: report['활동명'] || '',
                        font: "Arial", size: 24, color: "2E75B6"
                    })
                ]
            }),

            // 기본 정보 테이블
            new Table({
                width: { size: 9360, type: WidthType.DXA },
                columnWidths: [2500, 6860],
                rows: [
                    makeRow("■ 활동명", report['활동명']),
                    makeRow("■ 봉사분류", report['봉사분류']),
                    makeRow("■ 활동일시", report['활동일시']),
                    makeRow("■ 수혜자", report['수혜자수']),
                    makeRow("■ 활동장소", report['활동장소']),
                    makeRow("■ 내부봉사자", report['내부봉사자'] ? `${report['내부봉사자']}명` : "-"),
                    makeRow("■ 외부봉사자", report['외부봉사자'] ? `${report['외부봉사자']}명` : "-"),
                    makeRow("■ 총봉사자", report['총봉사자'] ? `${report['총봉사자']}명` : "-"),
                ]
            }),

            new Paragraph({ spacing: { before: 300 } }),

            // 활동내용
            ...makeSection("1. 활동 내용", report['활동내용']),

            // 반응 및 특이사항
            ...makeSection("2. 반응 및 특이사항", report['반응특이사항']),

            // 참여인사
            ...makeSection("3. 참여인사", report['참여인사']),

            // 홍보도구
            ...makeSection("4. 홍보도구", report['홍보도구']),

            // 잘된점
            ...makeSection("5. 잘된 점", report['잘된점']),

            // 개선할점
            ...makeSection("6. 개선할 점", report['개선할점']),

            // 등록일시
            new Paragraph({
                alignment: AlignmentType.RIGHT,
                spacing: { before: 400 },
                children: [
                    new TextRun({
                        text: `등록일시: ${report['등록일시'] || ''}`,
                        font: "Arial", size: 18, color: "888888"
                    })
                ]
            })
        ]
    }]
});

const outputPath = process.argv[3] || '/tmp/report.docx';
Packer.toBuffer(doc).then(buffer => {
    fs.writeFileSync(outputPath, buffer);
    console.log(`✅ Word 파일 생성 완료: ${outputPath}`);
}).catch(err => {
    console.error(`❌ 오류: ${err}`);
    process.exit(1);
});
