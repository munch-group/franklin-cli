

# ADDING CODE EXPLANATIONS JUPYTER NOTEBOOKS

Add a markdown cell after each code cell with an explanation the code. The explanaton should be formatted as a Markdown list wrapped in 

## Code cell 

```{python}
x = "hello"
print(x)
```


## Markdown cell 

<details>
<summary><small>Click to see what Franklin does</small></summary>

- First `x` is assigned the value `"hello"`
- Then the `print` function prints the value that the `x` value points to (`"hello"`).

</details>