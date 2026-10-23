-- Pandoc filter for the text module: shapes what pandoc's Markdown writer would otherwise keep in forms a reader
-- struggles with, or drop.

local function prose(block)
  return block.t == "Para" or block.t == "Plain"
end

-- A cell holding several paragraphs means prose set out as a table, as a dialogue sets each speech beside its
-- speaker. The Markdown writer can only keep it as a grid table, with the prose wrapped inside narrow cells, so
-- each row becomes paragraphs: a two-cell row as its first cell in bold, then the second; any other row cell by cell.
local function paragraphs(row)
  local cells = row.cells
  local out = pandoc.Blocks({})
  if #cells == 2 and #cells[1].contents == 1 and prose(cells[1].contents[1]) then
    local label = pandoc.Strong(cells[1].contents[1].content .. { pandoc.Str(":") })
    local body = pandoc.Blocks(cells[2].contents)
    if body[1] and prose(body[1]) then
      body[1] = pandoc.Para({ label, pandoc.Space() } .. body[1].content)
    else
      body:insert(1, pandoc.Para({ label }))
    end
    return body
  end
  for _, cell in ipairs(cells) do
    out:extend(cell.contents)
  end
  return out
end

function Table(tbl)
  local rows = {}
  local several = false
  for _, body in ipairs(tbl.bodies) do
    for _, row in ipairs(body.body) do
      table.insert(rows, row)
      for _, cell in ipairs(row.cells) do
        several = several or #cell.contents > 1
      end
    end
  end
  if not several then
    return nil
  end
  local out = pandoc.Blocks({})
  for _, row in ipairs(rows) do
    out:extend(paragraphs(row))
  end
  return out
end

-- The writer drops a caption it cannot fold into image syntax, so a figure becomes its content, then its
-- caption as an italic paragraph.
function Figure(fig)
  local out = pandoc.Blocks(fig.content)
  for _, block in ipairs(fig.caption.long) do
    if prose(block) then
      out:insert(pandoc.Para({ pandoc.Emph(block.content) }))
    else
      out:insert(block)
    end
  end
  return out
end
