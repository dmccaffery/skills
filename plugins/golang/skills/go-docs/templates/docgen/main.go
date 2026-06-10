// Command docgen renders the CLI reference from the cobra command tree, one
// page per command, for humans, search engines, and LLMs.
//
// It imports the application's command package, so it lives in the
// application module and runs as `go run ./internal/tools/docgen` — it is not
// a pinned developer tool in tools/go.mod.
package main

import (
	"flag"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strings"

	"github.com/spf13/cobra/doc"

	"example.com/myapp/internal/cli" // replace with your command package
)

func main() {
	out := flag.String("out", "docs/cli", "output directory")
	format := flag.String("format", "markdown", "markdown|man|rest")
	front := flag.Bool("frontmatter", false, "prepend YAML front matter to markdown pages")
	flag.Parse()

	if err := os.MkdirAll(*out, 0o755); err != nil {
		log.Fatal(err)
	}

	root := cli.Root()
	root.DisableAutoGenTag = true // stable, reproducible files — no timestamp footer

	var err error
	switch *format {
	case "markdown":
		if *front {
			err = doc.GenMarkdownTreeCustom(root, *out, frontmatter, linkHandler)
		} else {
			err = doc.GenMarkdownTree(root, *out)
		}
	case "man":
		hdr := &doc.GenManHeader{Title: strings.ToUpper(root.Name()), Section: "1"}
		err = doc.GenManTree(root, hdr, *out)
	case "rest":
		err = doc.GenReSTTree(root, *out)
	default:
		err = fmt.Errorf("unknown format %q", *format)
	}
	if err != nil {
		log.Fatal(err)
	}
}

// frontmatter prepends minimal YAML front matter so static site generators
// can index the page.
func frontmatter(filename string) string {
	name := strings.TrimSuffix(filepath.Base(filename), filepath.Ext(filename))
	title := strings.ReplaceAll(name, "_", " ")
	return fmt.Sprintf("---\ntitle: %q\nslug: %q\ndescription: \"CLI reference for %s\"\n---\n\n", title, name, title)
}

// linkHandler rewrites inter-page links; lower-casing keeps them stable on
// case-insensitive filesystems.
func linkHandler(name string) string { return strings.ToLower(name) }
