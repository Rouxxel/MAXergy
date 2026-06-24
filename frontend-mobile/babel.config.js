module.exports = function (api) {
  const isTest = api.env('test');
  api.cache(true);

  if (isTest) {
    return {
      presets: [
        ["babel-preset-expo"],
        ["@babel/preset-react", { runtime: "automatic" }],
        ["@babel/preset-typescript"],
      ],
      plugins: [],
    };
  }

  return {
    presets: [
      ["babel-preset-expo", { jsxImportSource: "nativewind" }],
      "nativewind/babel",
    ],
    plugins: [],
  };
};
