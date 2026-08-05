export function averageHash(matrix) {
  const flat = matrix.flat();
  if (flat.length !== 64) throw new Error("averageHash expects an 8x8 matrix");
  const avg = flat.reduce((sum, value) => sum + value, 0) / flat.length;
  return flat.map((value) => (value >= avg ? "1" : "0")).join("");
}

export function hammingDistance(left, right) {
  if (left.length !== right.length) throw new Error("Hashes must have the same length");
  let distance = 0;
  for (let index = 0; index < left.length; index += 1) {
    if (left[index] !== right[index]) distance += 1;
  }
  return distance;
}

export function similarityFromHash(left, right) {
  return 1 - hammingDistance(left, right) / left.length;
}

export const fixtures = {
  brightSquare: Array.from({ length: 8 }, (_, y) => Array.from({ length: 8 }, (_, x) => (x >= 2 && x <= 5 && y >= 2 && y <= 5 ? 240 : 20))),
  brightSquareCompressed: Array.from({ length: 8 }, (_, y) => Array.from({ length: 8 }, (_, x) => (x >= 2 && x <= 5 && y >= 2 && y <= 5 ? 220 : 35))),
  darkDiagonal: Array.from({ length: 8 }, (_, y) => Array.from({ length: 8 }, (_, x) => (x === y ? 240 : 20)))
};
