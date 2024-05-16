from scripts.xyz_grid import (
    AxisInfo,
    re_range,
    re_range_float,
    re_range_count,
    re_range_count_float,
    str_permutations,
    SharedSettingsStackHelper,
    draw_xyz_grid,
)

from scripts.adv_xyz_components import (
    MainInputsXYZ,
    SettingCheckboxs,
    ImageOptions,
    SwapButtons,
    SwapButtonsHook,
    FillButtonHook,
    TypeModeHooks,
    ClearHook,
    get_options,
)

from modules import scripts, images, errors, shared
from modules.processing import process_images, Processed, fix_seed, create_infotext

from itertools import permutations
from copy import copy
from PIL import Image

import numpy as np
import random


class AdvScript(scripts.Script):

    def __init__(self):
        self.is_i2i: bool = None

    def title(self):
        return "Adv. X/Y/Z Plot"

    def ui(self, is_img2img):
        self.is_i2i = is_img2img

        (
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
        ) = MainInputsXYZ(self, is_img2img)

        (
            draw_legend,
            no_fixed_seeds,
            vary_seeds_x,
            vary_seeds_y,
            vary_seeds_z,
            include_lone_images,
            include_sub_grids,
            csv_mode,
            delimiter,
        ) = SettingCheckboxs(self)

        margin_size, row_count = ImageOptions(self)

        (swap_xy_btn, swap_yz_btn, swap_xz_btn, clear_btn) = SwapButtons(self)

        SwapButtonsHook(
            swap_xy_btn,
            is_img2img,
            [x_type, x_values, x_values_dropdown, y_type, y_values, y_values_dropdown],
        )

        SwapButtonsHook(
            swap_yz_btn,
            is_img2img,
            [y_type, y_values, y_values_dropdown, z_type, z_values, z_values_dropdown],
        )

        SwapButtonsHook(
            swap_xz_btn,
            is_img2img,
            [x_type, x_values, x_values_dropdown, z_type, z_values, z_values_dropdown],
        )

        FillButtonHook(
            fill_x_button,
            x_type,
            csv_mode,
            x_values,
            x_values_dropdown,
            delimiter,
            is_img2img,
        )

        FillButtonHook(
            fill_y_button,
            y_type,
            csv_mode,
            y_values,
            y_values_dropdown,
            delimiter,
            is_img2img,
        )

        FillButtonHook(
            fill_z_button,
            z_type,
            csv_mode,
            z_values,
            x_values_dropdown,
            delimiter,
            is_img2img,
        )

        TypeModeHooks(
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
        )

        ClearHook(
            clear_btn,
            is_img2img,
            [
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
            ],
        )

        return [
            x_type,
            x_values,
            x_values_dropdown,
            y_type,
            y_values,
            y_values_dropdown,
            z_type,
            z_values,
            z_values_dropdown,
            draw_legend,
            include_lone_images,
            include_sub_grids,
            no_fixed_seeds,
            vary_seeds_x,
            vary_seeds_y,
            vary_seeds_z,
            margin_size,
            csv_mode,
            delimiter,
            row_count,
        ]

    def run(
        self,
        p,
        x_type: int,
        x_values: str,
        x_values_dropdown: list,
        y_type: int,
        y_values: str,
        y_values_dropdown: list,
        z_type: int,
        z_values: str,
        z_values_dropdown: list,
        draw_legend: bool,
        include_lone_images: bool,
        include_sub_grids: bool,
        no_fixed_seeds: bool,
        vary_seeds_x: bool,
        vary_seeds_y: bool,
        vary_seeds_z: bool,
        margin_size: int,
        csv_mode: bool,
        delimiter: str,
        row_count: int,
    ):

        x_type = 0 if x_type is None else x_type
        y_type = 0 if y_type is None else y_type
        z_type = 0 if z_type is None else z_type

        if (row_count > 1) and ((x_type == 0) or (y_type + z_type > 0)):
            print("\n\n[Error] Row Count only supports X Axis...\n\n")
            x_type = y_type = z_type = 0

        current_axis_options = get_options(self.is_i2i)

        delimiter = delimiter.strip()
        if not delimiter:
            delimiter = ","

        if not no_fixed_seeds:
            fix_seed(p)

        if not getattr(shared.opts, "return_grid", False):
            p.batch_size = 1

        def process_axis(opt, vals, vals_dropdown):
            if opt.label == "Nothing":
                return [0]

            if (opt.choices is not None) and (not csv_mode):
                valslist = vals_dropdown
            elif opt.prepare is not None:
                valslist = opt.prepare(vals)
            else:
                valslist = [val.strip() for val in vals.split(delimiter)]

            if opt.type == int:
                valslist_ext = []

                for val in valslist:
                    if not val.strip():
                        continue

                    m = re_range.fullmatch(val)
                    mc = re_range_count.fullmatch(val)

                    if m is not None:
                        start = int(m.group(1))
                        end = int(m.group(2)) + 1
                        step = int(m.group(3)) if m.group(3) is not None else 1

                        valslist_ext += list(range(start, end, step))

                    elif mc is not None:
                        start = int(mc.group(1))
                        end = int(mc.group(2))
                        num = int(mc.group(3)) if mc.group(3) is not None else 1

                        valslist_ext += [
                            int(x)
                            for x in np.linspace(
                                start=start, stop=end, num=num
                            ).tolist()
                        ]

                    else:
                        valslist_ext.append(val)

                valslist = valslist_ext

            elif opt.type == float:
                valslist_ext = []

                for val in valslist:
                    if not val.strip():
                        continue

                    m = re_range_float.fullmatch(val)
                    mc = re_range_count_float.fullmatch(val)

                    if m is not None:
                        start = float(m.group(1))
                        end = float(m.group(2))
                        step = float(m.group(3)) if m.group(3) is not None else 1

                        valslist_ext += np.arange(start, end + step, step).tolist()

                    elif mc is not None:
                        start = float(mc.group(1))
                        end = float(mc.group(2))
                        num = int(mc.group(3)) if mc.group(3) is not None else 1

                        valslist_ext += np.linspace(
                            start=start, stop=end, num=num
                        ).tolist()

                    else:
                        valslist_ext.append(val)

                valslist = valslist_ext

            elif opt.type == str_permutations:
                valslist = list(permutations(valslist))

            valslist = [opt.type(x) for x in valslist]

            if opt.confirm:
                opt.confirm(p, valslist)

            return valslist

        x_opt = current_axis_options[x_type]
        if x_opt.choices is not None and not csv_mode:
            x_values = delimiter.join(x_values_dropdown)
        xs = process_axis(x_opt, x_values, x_values_dropdown)

        y_opt = current_axis_options[y_type]
        if y_opt.choices is not None and not csv_mode:
            y_values = delimiter.join(y_values_dropdown)
        ys = process_axis(y_opt, y_values, y_values_dropdown)

        z_opt = current_axis_options[z_type]
        if z_opt.choices is not None and not csv_mode:
            z_values = delimiter.join(z_values_dropdown)
        zs = process_axis(z_opt, z_values, z_values_dropdown)

        Image.MAX_IMAGE_PIXELS = None
        grid_mp = round(len(xs) * len(ys) * len(zs) * p.width * p.height / 1000000)
        assert grid_mp < getattr(
            shared.opts, "img_max_size_mp", 4096
        ), f"Error: Resulting grid would be too large ({grid_mp} MPixels) (max configured size is {getattr(shared.opts, 'img_max_size_mp', 4096)} MPixels)"

        def fix_axis_seeds(axis_opt, axis_list):
            if axis_opt.label in ["Seed", "Var. seed"]:
                return [
                    (
                        int(random.randrange(4294967294))
                        if val is None or val == "" or val == -1
                        else val
                    )
                    for val in axis_list
                ]
            else:
                return axis_list

        if not no_fixed_seeds:
            xs = fix_axis_seeds(x_opt, xs)
            ys = fix_axis_seeds(y_opt, ys)
            zs = fix_axis_seeds(z_opt, zs)

        if x_opt.label == "Steps":
            total_steps = sum(xs) * len(ys) * len(zs)
        elif y_opt.label == "Steps":
            total_steps = sum(ys) * len(xs) * len(zs)
        elif z_opt.label == "Steps":
            total_steps = sum(zs) * len(xs) * len(ys)
        else:
            total_steps = p.steps * len(xs) * len(ys) * len(zs)

        if getattr(p, "enable_hr", False):
            if x_opt.label == "Hires steps":
                total_steps += sum(xs) * len(ys) * len(zs)
            elif y_opt.label == "Hires steps":
                total_steps += sum(ys) * len(xs) * len(zs)
            elif z_opt.label == "Hires steps":
                total_steps += sum(zs) * len(xs) * len(ys)
            elif p.hr_second_pass_steps:
                total_steps += p.hr_second_pass_steps * len(xs) * len(ys) * len(zs)
            else:
                total_steps *= 2

        total_steps *= p.n_iter

        image_cell_count = p.n_iter * p.batch_size
        cell_console_text = (
            f"; {image_cell_count} images per cell" if image_cell_count > 1 else ""
        )
        plural_s = "s" if len(zs) > 1 else ""
        print(
            f"X/Y/Z plot will create {len(xs) * len(ys) * len(zs) * image_cell_count} images on {len(zs)} {len(xs)}x{len(ys)} grid{plural_s}{cell_console_text}. (Total steps to process: {total_steps})"
        )
        shared.total_tqdm.updateTotal(total_steps)

        shared.state.xyz_plot_x = AxisInfo(x_opt, xs)
        shared.state.xyz_plot_y = AxisInfo(y_opt, ys)
        shared.state.xyz_plot_z = AxisInfo(z_opt, zs)

        first_axes_processed = "z"
        second_axes_processed = "y"
        if x_opt.cost > y_opt.cost and x_opt.cost > z_opt.cost:
            first_axes_processed = "x"
            if y_opt.cost > z_opt.cost:
                second_axes_processed = "y"
            else:
                second_axes_processed = "z"
        elif y_opt.cost > x_opt.cost and y_opt.cost > z_opt.cost:
            first_axes_processed = "y"
            if x_opt.cost > z_opt.cost:
                second_axes_processed = "x"
            else:
                second_axes_processed = "z"
        elif z_opt.cost > x_opt.cost and z_opt.cost > y_opt.cost:
            first_axes_processed = "z"
            if x_opt.cost > y_opt.cost:
                second_axes_processed = "x"
            else:
                second_axes_processed = "y"

        grid_infotext = [None] * (1 + len(zs))

        def cell(x, y, z, ix, iy, iz):
            if shared.state.interrupted or shared.state.stopping_generation:
                return Processed(p, [], p.seed, "")

            pc = copy(p)
            pc.styles = pc.styles[:]
            x_opt.apply(pc, x, xs)
            y_opt.apply(pc, y, ys)
            z_opt.apply(pc, z, zs)

            xdim = len(xs) if vary_seeds_x else 1
            ydim = len(ys) if vary_seeds_y else 1

            if vary_seeds_x:
                pc.seed += ix
            if vary_seeds_y:
                pc.seed += iy * xdim
            if vary_seeds_z:
                pc.seed += iz * xdim * ydim

            try:
                res = process_images(pc)
            except Exception as e:
                errors.display(e, "generating image for xyz plot")

                res = Processed(p, [], p.seed, "")

            subgrid_index = 1 + iz
            if grid_infotext[subgrid_index] is None and ix == 0 and iy == 0:
                pc.extra_generation_params = copy(pc.extra_generation_params)
                pc.extra_generation_params["Script"] = self.title()

                if x_opt.label != "Nothing":
                    pc.extra_generation_params["X Type"] = x_opt.label
                    pc.extra_generation_params["X Values"] = x_values
                    if x_opt.label in ["Seed", "Var. seed"] and not no_fixed_seeds:
                        pc.extra_generation_params["Fixed X Values"] = ", ".join(
                            [str(x) for x in xs]
                        )

                if y_opt.label != "Nothing":
                    pc.extra_generation_params["Y Type"] = y_opt.label
                    pc.extra_generation_params["Y Values"] = y_values
                    if y_opt.label in ["Seed", "Var. seed"] and not no_fixed_seeds:
                        pc.extra_generation_params["Fixed Y Values"] = ", ".join(
                            [str(y) for y in ys]
                        )

                grid_infotext[subgrid_index] = create_infotext(
                    pc, pc.all_prompts, pc.all_seeds, pc.all_subseeds
                )

            if grid_infotext[0] is None and ix == 0 and iy == 0 and iz == 0:
                pc.extra_generation_params = copy(pc.extra_generation_params)

                if z_opt.label != "Nothing":
                    pc.extra_generation_params["Z Type"] = z_opt.label
                    pc.extra_generation_params["Z Values"] = z_values
                    if z_opt.label in ["Seed", "Var. seed"] and not no_fixed_seeds:
                        pc.extra_generation_params["Fixed Z Values"] = ", ".join(
                            [str(z) for z in zs]
                        )

                grid_infotext[0] = create_infotext(
                    pc, pc.all_prompts, pc.all_seeds, pc.all_subseeds
                )

            return res

        with SharedSettingsStackHelper():
            processed = draw_xyz_grid(
                p,
                xs=xs,
                ys=ys,
                zs=zs,
                x_labels=[x_opt.format_value(p, x_opt, x) for x in xs],
                y_labels=[y_opt.format_value(p, y_opt, y) for y in ys],
                z_labels=[z_opt.format_value(p, z_opt, z) for z in zs],
                cell=cell,
                draw_legend=draw_legend,
                include_lone_images=include_lone_images,
                include_sub_grids=include_sub_grids,
                first_axes_processed=first_axes_processed,
                second_axes_processed=second_axes_processed,
                margin_size=margin_size,
            )

        if not processed.images:
            return processed

        z_count = len(zs)

        processed.infotexts[: 1 + z_count] = grid_infotext[: 1 + z_count]

        if not include_lone_images:
            processed.images = processed.images[: z_count + 1]

        if getattr(shared.opts, "grid_save", True):
            grid_count = z_count + 1 if z_count > 1 else 1
            for g in range(grid_count):
                # TODO: See previous comment about intentional data misalignment.
                adj_g = g - 1 if g > 0 else g
                images.save_image(
                    processed.images[g],
                    p.outpath_grids,
                    "xyz_grid",
                    info=processed.infotexts[g],
                    extension=getattr(shared.opts, "grid_format", "jpg"),
                    prompt=processed.all_prompts[adj_g],
                    seed=processed.all_seeds[adj_g],
                    grid=True,
                    p=processed,
                )
                if not include_sub_grids:
                    break

        if not include_sub_grids:
            for _ in range(z_count):
                del processed.images[1]
                del processed.all_prompts[1]
                del processed.all_seeds[1]
                del processed.infotexts[1]

        def rearrange_image(original_image: Image):
            width, height = original_image.size
            width_per_image = int(width // len(xs))

            target_count = min(row_count, len(xs))
            imgs_per_row = (len(xs) // target_count) + int(len(xs) % target_count != 0)

            print(f"Converting to {imgs_per_row}x{target_count} grid...")

            new_width = width_per_image * imgs_per_row
            new_height = height * target_count

            new_image = Image.new("RGB", (new_width, new_height), "white")

            for y in range(target_count):
                row = original_image.crop(
                    (
                        y * (width_per_image * imgs_per_row),
                        0,
                        min(width, ((y + 1) * (width_per_image * imgs_per_row))),
                        height,
                    )
                )
                new_image.paste(row, (0, height * y))

            return new_image

        if row_count > 1:
            processed.images[0] = rearrange_image(processed.images[0])

        return processed
