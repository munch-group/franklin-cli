function Header(el)
    if el.level == 4 then
      local name = pandoc.utils.stringify(el.content[3])
      local number = ""
      if el.attr then
        number = el.attr.attributes.number:gsub("%.0%.0%.", "-")
      end
      el.content =  pandoc.Strong(name .. " " .. number)
      return el
    end
  end
  

  -- local function flatten (lst)
  --   local res = List:new{}
  --   for i, el in ipairs(lst) do
  --   if el.t == 'Sec' then
  --   res[#res + 1] = pandoc.Header(el.level, el.label, el.attr)
  --   res:extend(flatten(el.contents))
  --   else
  --   res[#res + 1] = el
  --   end
  --   end
  --   return res
  --   end
    