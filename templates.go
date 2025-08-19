package plugins

import (
	"embed"
	"fmt"
	"io"
	"io/fs"
	"strings"
)

//go:embed plugins
var embeddedTemplates embed.FS

//go:embed spaceforge/schema.json
var jsonSchema string

// Templates returns the body of the raw manifests stored in the ./plugins folder.
func Templates() []string {
	results, err := parse(embeddedTemplates)
	if err != nil {
		panic("plugin lib: " + err.Error())
	}
	return results
}

// JSONSchema returns the JSON schema for the plugins.
func JSONSchema() string {
	return jsonSchema
}

func parse(f fs.FS) ([]string, error) {
	var result []string
	err := fs.WalkDir(f, ".", func(path string, _ fs.DirEntry, err error) error {
		if err != nil {
			return err
		}

		const yml = ".yml"
		const yaml = ".yaml"
		if !strings.HasSuffix(path, yml) && !strings.HasSuffix(path, yaml) {
			return nil
		}

		f, err := f.Open(path)
		if err != nil {
			return err
		}
		defer func() { _ = f.Close() }()

		body, err := io.ReadAll(f)
		if err != nil {
			return err
		}

		result = append(result, string(body))
		return nil
	})

	if err != nil {
		return nil, fmt.Errorf("templates: %w", err)
	}

	return result, nil
}
