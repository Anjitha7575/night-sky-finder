export const CATEGORIES = {
  meteor: { label: "Meteor", plural: "Meteors", color: "var(--meteor)" },
  satellite: { label: "Satellite", plural: "Satellites", color: "var(--satellite)" },
  plane: { label: "Plane", plural: "Planes", color: "var(--plane)" },
  bird: { label: "Bird", plural: "Birds", color: "var(--cloud)" },
  insect: { label: "Insect", plural: "Insects", color: "var(--cloud)" },
  cloud: { label: "Cloud", plural: "Clouds", color: "var(--cloud)" },
  flash: { label: "Sky flash", short: "Flash", plural: "Sky flashes", color: "var(--flash)" },
  not_sky: { label: "Not a sky video", short: "Not sky", plural: "Not sky", color: "var(--cloud)" },
  unsure: { label: "Not sure", short: "Unsure", plural: "Not sure", color: "var(--unsure)" },
};

export const ORDER = ["meteor", "satellite", "plane", "bird", "insect", "cloud", "flash", "not_sky", "unsure"];

export const categoryOf = (key) => CATEGORIES[key] || CATEGORIES.unsure;

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function describeName(name) {
  const file = name.split("/").pop();
  let expert = null;
  let rest = file;
  const parts = file.split("__");
  if (parts.length > 1 && ["meteor", "non_meteor"].includes(parts[0])) {
    expert = parts[0] === "meteor" ? "meteor" : "not a meteor";
    rest = parts.slice(1).join("__");
  }
  const m =
    rest.match(/(\d{4})[_-](\d{2})[_-](\d{2})(?:[_ -]+(\d{2})[_-](\d{2}))?/) ||
    rest.match(/^m(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})/);
  let when = null;
  let year = null;
  let sortKey = "";
  if (m) {
    year = m[1];
    sortKey = `${m[1]}${m[2]}${m[3]}${m[4] || "00"}${m[5] || "00"}`;
    when = `${Number(m[3])} ${MONTHS[Number(m[2]) - 1]} ${m[1]}`;
    if (m[4]) when += `, ${m[4]}:${m[5]}`;
  }
  let place = "Sample clip";
  if (/teide/i.test(rest)) {
    place = "Teide, Spain";
    year = year || "2016";
    sortKey = sortKey || "2016";
  }
  else if (/^m\d{8}_\d{6}/.test(rest) || /las cruces/i.test(rest)) place = "Las Cruces, USA";
  else if (expert) place = "AllSky7 network";
  return { file, expert, when, year, sortKey, place };
}
