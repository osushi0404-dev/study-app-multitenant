// annotation テスト用一時ファイル
const obj: any = {};
const key = "test";
const val = obj[key]; // security/detect-object-injection を意図的に発生させる
export default val;
