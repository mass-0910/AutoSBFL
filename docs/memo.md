# AutoSBFLの書き直しにおけるメモ

- evosuite-sbflとtestcase-selectorの2つの成果物が存在
- 「evosuite-sbflへのjacoco導入」と「evosuite-sbflへのtestcase-selectorの組み込み」を同時に行う

## evosuite-sbflへのjacoco導入

- ANTLRの必要はもうなさそう
- なんならjavalangの必要もない
- カバレッジ取るならjacoco + testcase-selector内のjacoco report解析コードが使えそう

## evosuite-sbflへのtestcase-selectorの組み込み

- evosuiteのテストをtestcase-selectorで厳選したテストに置換すればいけそう