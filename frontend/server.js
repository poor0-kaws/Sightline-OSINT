// `createServer` makes a tiny local web server with no extra packages.
import { createServer } from "http";
// `readFile` loads the static files from disk.
import { readFile } from "fs/promises";
// `extname` helps us pick the right content type for each file.
import { extname } from "path";
// `fileURLToPath` converts this module URL into a normal file path.
import { fileURLToPath } from "url";
// `dirname` lets us find the folder that contains this server file.
import { dirname } from "path";
// `join` builds safe file paths to files in `src/`.
import { join } from "path";

const currentFilePath = fileURLToPath(import.meta.url);
const currentDirectory = dirname(currentFilePath);
const sourceDirectory = join(currentDirectory, "src");

const contentTypes = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
};

const server = createServer(async (request, response) => {
  const requestedPath = request.url === "/" ? "/index.html" : request.url;
  const filePath = join(sourceDirectory, requestedPath);

  try {
    const fileContents = await readFile(filePath, "utf8");
    const extension = extname(filePath);
    response.writeHead(200, {
      "Content-Type": contentTypes[extension] || "text/plain; charset=utf-8",
    });
    response.end(fileContents);
    return;
  } catch (error) {
    response.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
    response.end("frontend skeleton ready");
    return;
  }
});

server.listen(4173, "127.0.0.1", () => {
  console.log("frontend skeleton ready at http://127.0.0.1:4173");
});

