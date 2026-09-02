from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock


class BlogStreamBlock(blocks.StreamBlock):

    # TEXT BLOCKS
    heading = blocks.CharBlock(
        required=True,
        help_text="Add a heading",
    )

    subheading = blocks.CharBlock(
        required=True,
        help_text="Add a subheading",
    )

    paragraph = blocks.RichTextBlock(
        required=True,
        help_text="Add paragraph content",
    )

    # LIST BLOCKS
    bullet_list = blocks.ListBlock(
        blocks.CharBlock()
    )

    numbered_list = blocks.ListBlock(
        blocks.CharBlock()
    )

    # MEDIA BLOCKS
    image = ImageChooserBlock()

    # SPECIAL CONTENT
    quote = blocks.BlockQuoteBlock()

    code = blocks.TextBlock(
        help_text="Add your code here",
        rows=10,
    )

    divider = blocks.StaticBlock(
        admin_text="Horizontal divider"
    )
