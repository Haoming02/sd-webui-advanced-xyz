from scripts.xyz_grid import fill_values_symbol
from modules.ui_components import ToolButton
from modules import scripts
import gradio as gr
import json
import os

xyz = None
config = None
config_path = os.path.join(scripts.basedir(), "config.json")


def get_options(is_img2img: bool) -> list:
    """Grab all available Types for the X/Y/Z Plot from the built-in script"""

    global xyz
    if xyz is None:
        for data in scripts.scripts_data:
            if data.script_class.__module__ in (
                "scripts.xyz_grid",
                "xyz_grid.py",
            ) and hasattr(data, "module"):
                xyz = data.module

    axis_options = xyz.axis_options

    global config
    if config is None:

        if not os.path.exists(config_path):
            config = {"show": [x.label for x in axis_options], "hide": []}
            with open(config_path, "w+", encoding="utf-8") as f:
                json.dump(config, f)

        else:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

    return [
        x
        for x in axis_options
        if (type(x) == xyz.AxisOption or x.is_img2img == is_img2img)
        and (x.label not in config["hide"])
    ]


def MainInputsXYZ(self, is_img2img) -> list[gr.component]:
    """
    The main input components which include:
      1. Type Dropdown
      2. Choice Dropdown / Text Field
      3. (Optional) Quick Fill Button
    for all three X/Y/Z axis
    """

    components = []
    with gr.Row(elem_id=self.elem_id("main_inputs")):
        with gr.Column(scale=19):

            for Axis, axis in (("X", "x"), ("Y", "y"), ("Z", "z")):
                with gr.Row():
                    components.append(
                        gr.Dropdown(
                            label=f"{Axis} type",
                            choices=[opt.label for opt in get_options(is_img2img)],
                            value=get_options(is_img2img)[0].label,
                            type="index",
                            elem_id=self.elem_id(f"{axis}_type"),
                        )
                    )
                    components.append(
                        gr.Textbox(
                            label=f"{Axis} values",
                            lines=1,
                            elem_id=self.elem_id(f"{axis}_values"),
                        )
                    )
                    components.append(
                        gr.Dropdown(
                            label=f"{Axis} values",
                            visible=False,
                            multiselect=True,
                            interactive=True,
                        )
                    )
                    components.append(
                        ToolButton(
                            value=fill_values_symbol,
                            elem_id=f"xyz_grid_fill_{axis}_tool_button",
                            visible=False,
                        )
                    )

    return components


def SettingCheckboxs(self) -> list[gr.component]:
    """
    Various checkboxs that affect the logics, including:
      - Settings for seeds
      - How the textfields are processed
    """

    components = []
    with gr.Row(variant="compact", elem_id=self.elem_id("axis_options")):

        with gr.Column():
            components.append(
                gr.Checkbox(
                    label="Draw legend",
                    value=True,
                    elem_id=self.elem_id("draw_legend"),
                )
            )
            components.append(
                gr.Checkbox(
                    label="Keep -1 for seeds",
                    value=False,
                    elem_id=self.elem_id("no_fixed_seeds"),
                )
            )
            for axis in ("X", "Y", "Z"):
                components.append(
                    gr.Checkbox(
                        label=f"Vary seeds for {axis}",
                        value=False,
                        min_width=80,
                        elem_id=self.elem_id(f"vary_seeds_{axis.lower()}"),
                        tooltip=f"Use different seeds for images along {axis} axis.",
                    )
                )

        with gr.Column():
            components.append(
                gr.Checkbox(
                    label="Include Sub Images",
                    value=False,
                    elem_id=self.elem_id("include_lone_images"),
                )
            )
            components.append(
                gr.Checkbox(
                    label="Include Sub Grids",
                    value=False,
                    elem_id=self.elem_id("include_sub_grids"),
                )
            )
            components.append(
                gr.Checkbox(
                    label="Use text inputs instead of dropdowns",
                    value=False,
                    elem_id=self.elem_id("csv_mode"),
                )
            )
            components.append(
                gr.Textbox(
                    value=",",
                    label="Delimiter",
                    lines=1,
                    max_lines=1,
                    elem_id=self.elem_id("delimiter"),
                    tooltip="Character used to separate each entry.",
                )
            )

    return components


def ImageOptions(self) -> list[gr.component]:
    """Misc. options that affect how the images are presented"""

    components = []
    with gr.Row(variant="compact", elem_id=self.elem_id("image_options")):

        components.append(
            gr.Slider(
                label="Grid margins (pixel)",
                minimum=0,
                maximum=256,
                value=0,
                step=2,
                elem_id=self.elem_id("margin_size"),
            )
        )
        components.append(
            gr.Slider(
                label="Row Count",
                minimum=1,
                maximum=8,
                value=1,
                step=1,
                elem_id=self.elem_id("row_count"),
                tooltip="(Only for X Axis) Break up the images into this number of rows.",
            )
        )

    return components


def SwapButtons(self) -> list[gr.component]:
    """Buttons for Swapping Axis"""

    components = []
    with gr.Column(variant="compact", elem_id=self.elem_id("swap_axes")):
        with gr.Row():
            components.append(
                gr.Button(value="Swap X/Y axes", elem_id="xy_grid_swap_axes_button")
            )
            components.append(
                gr.Button(value="Swap Y/Z axes", elem_id="yz_grid_swap_axes_button")
            )
            components.append(
                gr.Button(value="Swap X/Z axes", elem_id="xz_grid_swap_axes_button")
            )

        components.append(gr.Button(value="Clear"))

    return components


def SwapButtonsHook(btn, is_img2img, args: list):
    """Handle the logics of the Swap Buttons"""

    def swap(
        axis1_type,
        axis1_values,
        axis1_dropdown,
        axis2_type,
        axis2_values,
        axis2_dropdown,
    ):
        return (
            get_options(is_img2img)[axis2_type].label,
            axis2_values,
            axis2_dropdown,
            get_options(is_img2img)[axis1_type].label,
            axis1_values,
            axis1_dropdown,
        )

    btn.click(swap, inputs=args, outputs=args)


def FillButtonHook(btn, _type, _csv, _value, _dropdown, _delimiter, is_img2img):
    """Handle the logics of the Fill Buttons"""

    def fill(axis_type: int, csv_mode: bool, delimiter: str):
        choices: function = get_options(is_img2img)[axis_type].choices

        if choices is not None:
            if csv_mode:
                return delimiter.join(choices()).strip(), gr.update()
            else:
                return gr.update(), choices()
        else:
            return gr.update(), gr.update()

    btn.click(fn=fill, inputs=[_type, _csv, _delimiter], outputs=[_value, _dropdown])


def TypeModeHooks(
    csv_mode,
    x_type,
    x_values,
    x_values_dropdown,
    fill_x_button,
    y_type,
    y_values,
    y_values_dropdown,
    fill_y_button,
    z_type,
    z_values,
    z_values_dropdown,
    fill_z_button,
    delimiter,
    is_img2img,
):
    """
    Handle the logics when:
      - An Axis's Type was changed
      - The CSV mode was changed
    """

    def select_axis(axis_type, axis_values, axis_values_dropdown, _delimiter, mode):
        axis_type = 0 if axis_type is None else axis_type

        choices: function = get_options(is_img2img)[axis_type].choices
        has_choices: bool = choices is not None

        if has_choices:
            choices = choices()

            if mode:
                if axis_values_dropdown:
                    axis_values = _delimiter.join(
                        list(filter(lambda x: x in choices, axis_values_dropdown))
                    ).strip()
                    axis_values_dropdown = []

            else:
                if axis_values:
                    axis_values_dropdown = list(
                        filter(
                            lambda x: x in choices,
                            [val.strip() for val in axis_values.split(_delimiter)],
                        )
                    )
                    axis_values = ""

        return (
            gr.Button.update(visible=has_choices),
            gr.Textbox.update(visible=(not has_choices or mode), value=axis_values),
            gr.update(
                choices=choices if has_choices else None,
                visible=has_choices and not mode,
                value=axis_values_dropdown,
            ),
        )

    x_type.change(
        fn=select_axis,
        inputs=[x_type, x_values, x_values_dropdown, delimiter, csv_mode],
        outputs=[fill_x_button, x_values, x_values_dropdown],
    )

    y_type.change(
        fn=select_axis,
        inputs=[y_type, y_values, y_values_dropdown, delimiter, csv_mode],
        outputs=[fill_y_button, y_values, y_values_dropdown],
    )

    z_type.change(
        fn=select_axis,
        inputs=[z_type, z_values, z_values_dropdown, delimiter, csv_mode],
        outputs=[fill_z_button, z_values, z_values_dropdown],
    )

    def onModeChange(*args):
        mode = args[0]
        _delimiter = args[1]
        _t1, _v1, _d1 = args[2:5]
        _t2, _v2, _d2 = args[5:8]
        _t3, _v3, _d3 = args[8:11]

        return (
            select_axis(_t1, _v1, _d1, _delimiter, mode)
            + select_axis(_t2, _v2, _d2, _delimiter, mode)
            + select_axis(_t3, _v3, _d3, _delimiter, mode)
        )

    csv_mode.change(
        fn=onModeChange,
        inputs=[
            csv_mode,
            delimiter,
            x_type,
            x_values,
            x_values_dropdown,
            y_type,
            y_values,
            y_values_dropdown,
            z_type,
            z_values,
            z_values_dropdown,
        ],
        outputs=[
            fill_x_button,
            x_values,
            x_values_dropdown,
            fill_y_button,
            y_values,
            y_values_dropdown,
            fill_z_button,
            z_values,
            z_values_dropdown,
        ],
    )


def ClearHook(clear_btn, is_img2img, args: list):
    """Handle the logics of the Clear Button"""

    def onClear():
        return (
            gr.Dropdown.update(value=get_options(is_img2img)[0].label),
            gr.Textbox.update(value=""),
            gr.Dropdown.update(value=[]),
            gr.Button.update(visible=False),
            gr.Dropdown.update(value=get_options(is_img2img)[0].label),
            gr.Textbox.update(value=""),
            gr.Dropdown.update(value=[]),
            gr.Button.update(visible=False),
            gr.Dropdown.update(value=get_options(is_img2img)[0].label),
            gr.Textbox.update(value=""),
            gr.Dropdown.update(value=[]),
            gr.Button.update(visible=False),
        )

    clear_btn.click(
        fn=onClear,
        inputs=None,
        outputs=args,
    )
