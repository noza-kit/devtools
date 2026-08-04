// このファイルはコメント翻訳のデモ用サンプルです
// 複数行のコメントもまとめて翻訳される想定
function greet(name) {
  /* 挨拶メッセージを組み立てる処理
     複数行のブロックコメントもサポートする */
  const message = "Hello, " + name; // 末尾に感嘆符は付けない

  return message;
}

module.exports = { greet };
