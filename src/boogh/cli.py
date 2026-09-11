"""boogh cli is argument parsing and dispatch."""
import argparse
import json
import sys
import urllib.error

from boogh.auth import Auth
from boogh.food import Food
from boogh.geo import Geo
from boogh.login import Login
from boogh.net import Net
from boogh.ride import Ride
from boogh.vault import Vault


def hub():
    vault = Vault()
    net = Net(vault)
    auth = Auth(vault, net)
    geo = Geo(vault, net, auth)
    return Food(vault, net, auth), Ride(vault, net, auth, geo), Login(vault, net, auth), geo


def confirm(parser):
    parser.add_argument("--confirm", action="store_true")


def token(parser):
    parser.add_argument("--token")


def where(parser):
    parser.add_argument("--lat")
    parser.add_argument("--long")


def vendor(parser):
    parser.add_argument("code")
    where(parser)


def body(parser):
    parser.add_argument("--body-json")
    parser.add_argument("--body-file")
    token(parser)


def trip(parser):
    parser.add_argument("--from-lat", type=float)
    parser.add_argument("--from-lng", type=float)
    parser.add_argument("--to-lat", type=float)
    parser.add_argument("--to-lng", type=float)
    parser.add_argument("--origin")
    parser.add_argument("--dest")


def food_group(sub, food, login):
    parser = sub.add_parser("food")
    branch = parser.add_subparsers(dest="op", required=True)

    branch.add_parser("cities").set_defaults(func=food.cities)
    area = branch.add_parser("area")
    where(area)
    area.set_defaults(func=food.area)
    vendors = branch.add_parser("vendors")
    where(vendors)
    vendors.add_argument("--supertype")
    vendors.add_argument("--page")
    vendors.add_argument("--compact", action="store_true")
    vendors.set_defaults(func=food.vendors)
    for name, fn in [("vendor", food.vendor), ("menu", food.menu), ("reviews", food.reviews)]:
        leaf = branch.add_parser(name)
        vendor(leaf)
        leaf.set_defaults(func=fn)
    place = branch.add_parser("place")
    place.add_argument("--place", required=True)
    where(place)
    place.set_defaults(func=food.place)
    reverse = branch.add_parser("reverse")
    where(reverse)
    reverse.set_defaults(func=food.reverse)
    for name, fn in [("profile", food.profile), ("pending", food.pending),
                     ("detail", food.detail)]:
        leaf = branch.add_parser(name)
        token(leaf)
        leaf.set_defaults(func=fn)
    rules = branch.add_parser("rules")
    rules.add_argument("code")
    token(rules)
    rules.set_defaults(func=food.rules)

    basket = branch.add_parser("basket").add_subparsers(dest="act", required=True)
    create = basket.add_parser("create")
    body(create)
    confirm(create)
    create.set_defaults(func=food.basket_create)
    update = basket.add_parser("update")
    update.add_argument("basket_id")
    body(update)
    confirm(update)
    update.set_defaults(func=food.basket_update)
    delete = basket.add_parser("delete")
    delete.add_argument("basket_id")
    token(delete)
    confirm(delete)
    delete.set_defaults(func=food.basket_delete)

    order = branch.add_parser("order").add_subparsers(dest="act", required=True)
    new = order.add_parser("new")
    body(new)
    new.add_argument("--provider")
    confirm(new)
    new.set_defaults(func=food.order_new)

    review = branch.add_parser("review").add_subparsers(dest="act", required=True)
    submit = review.add_parser("submit")
    submit.add_argument("--order-id", required=True)
    submit.add_argument("--comment", default="")
    submit.add_argument("--rate", type=float)
    token(submit)
    confirm(submit)
    submit.set_defaults(func=food.review_submit)

    auth = branch.add_parser("login").add_subparsers(dest="act", required=True)
    send = auth.add_parser("send")
    send.add_argument("--phone", required=True)
    send.add_argument("--via", default="heimdall", choices=["heimdall", "legacy"])
    send.set_defaults(func=login.food_send)
    verify = auth.add_parser("verify")
    verify.add_argument("--phone", required=True)
    verify.add_argument("--code", required=True)
    verify.add_argument("--via", default="heimdall", choices=["heimdall", "legacy"])
    verify.set_defaults(func=login.food_verify)
    refresh = auth.add_parser("refresh")
    refresh.set_defaults(func=login.food_refresh)


def ride_group(sub, ride, login):
    parser = sub.add_parser("ride")
    branch = parser.add_subparsers(dest="op", required=True)

    price = branch.add_parser("price")
    trip(price)
    price.add_argument("--compact", action="store_true")
    price.add_argument("--voucher")
    token(price)
    price.set_defaults(func=ride.price)
    request = branch.add_parser("request")
    trip(request)
    request.add_argument("--service", type=int, default=1)
    token(request)
    confirm(request)
    request.set_defaults(func=ride.request)
    cancel = branch.add_parser("cancel")
    cancel.add_argument("ride_id")
    cancel.add_argument("--state", default="passenger")
    cancel.add_argument("--reason")
    token(cancel)
    confirm(cancel)
    cancel.set_defaults(func=ride.cancel)
    reasons = branch.add_parser("reasons")
    reasons.add_argument("ride_id")
    token(reasons)
    reasons.set_defaults(func=ride.reasons)
    for name, fn in [("status", ride.status), ("rating", ride.rating),
                     ("debts", ride.debts), ("wallets", ride.wallets),
                     ("balance", ride.balance)]:
        leaf = branch.add_parser(name)
        token(leaf)
        leaf.set_defaults(func=fn)
    history = branch.add_parser("history")
    history.add_argument("--page", type=int)
    history.add_argument("--limit", type=int, default=10)
    token(history)
    history.set_defaults(func=ride.history)
    headsup = branch.add_parser("headsup")
    headsup.add_argument("ride_id")
    token(headsup)
    headsup.set_defaults(func=ride.headsup)

    profile = branch.add_parser("profile").add_subparsers(dest="act")
    show = profile.add_parser("show", help="show profile")
    token(show)
    show.set_defaults(func=ride.profile)
    edit = profile.add_parser("set")
    edit.add_argument("--name", required=True)
    edit.add_argument("--gender")
    edit.add_argument("--birthdate")
    edit.add_argument("--address")
    token(edit)
    confirm(edit)
    edit.set_defaults(func=ride.profile_set)

    place = branch.add_parser("place").add_subparsers(dest="act")
    listing = place.add_parser("list", help="list saved places")
    token(listing)
    listing.set_defaults(func=ride.places)
    add = place.add_parser("add")
    add.add_argument("--name", required=True)
    add.add_argument("--address", default="")
    add.add_argument("--lat", type=float, required=True)
    add.add_argument("--lng", type=float, required=True)
    token(add)
    confirm(add)
    add.set_defaults(func=ride.place_add)

    auth = branch.add_parser("login").add_subparsers(dest="act", required=True)
    send = auth.add_parser("send")
    send.add_argument("--phone", required=True)
    send.add_argument("--captcha-client")
    send.add_argument("--captcha-ref")
    send.add_argument("--captcha-solution")
    send.add_argument("--captcha-out", default="/tmp/opencode/ride_captcha.jpg")
    send.set_defaults(func=login.ride_send)
    verify = auth.add_parser("verify")
    verify.add_argument("--phone", required=True)
    verify.add_argument("--code", required=True)
    verify.add_argument("--method", default="voice")
    verify.set_defaults(func=login.ride_verify)
    imp = auth.add_parser("import")
    imp.add_argument("--access")
    imp.add_argument("--refresh")
    imp.add_argument("--device")
    imp.set_defaults(func=login.ride_import)
    refresh = auth.add_parser("refresh")
    refresh.add_argument("--refresh")
    refresh.set_defaults(func=login.ride_refresh)
    guided = auth.add_parser("guided")
    guided.add_argument("--timeout", type=int, default=300)
    guided.set_defaults(func=login.ride_guided)

    voucher = branch.add_parser("voucher").add_subparsers(dest="act", required=True)
    apply = voucher.add_parser("apply")
    apply.add_argument("--code", required=True)
    token(apply)
    confirm(apply)
    apply.set_defaults(func=ride.voucher)
    debt = branch.add_parser("debt").add_subparsers(dest="act", required=True)
    pay = debt.add_parser("pay")
    pay.add_argument("--wallet", type=int, default=0)
    token(pay)
    confirm(pay)
    pay.set_defaults(func=ride.debt)
    options = branch.add_parser("options").add_subparsers(dest="act", required=True)
    quote = options.add_parser("quote")
    quote.add_argument("--from-lat", required=True)
    quote.add_argument("--from-lng", required=True)
    quote.add_argument("--to-lat", required=True)
    quote.add_argument("--to-lng", required=True)
    quote.add_argument("--service", type=int, default=1)
    token(quote)
    confirm(quote)
    quote.set_defaults(func=ride.options)
    edit = options.add_parser("set")
    edit.add_argument("--disabilities", default="")
    token(edit)
    confirm(edit)
    edit.set_defaults(func=ride.options_set)
    flexi = branch.add_parser("flexi")
    flexi.add_argument("--from-lat", required=True)
    flexi.add_argument("--from-lng", required=True)
    flexi.add_argument("--to-lat", required=True)
    flexi.add_argument("--to-lng", required=True)
    flexi.add_argument("--service", type=int, default=1)
    token(flexi)
    confirm(flexi)
    flexi.set_defaults(func=ride.flexi)
    clone = branch.add_parser("clone")
    clone.add_argument("ride_id")
    clone.add_argument("--reason-id", type=int, default=0)
    token(clone)
    confirm(clone)
    clone.set_defaults(func=ride.clone)
    block = branch.add_parser("block")
    block.add_argument("ride_id")
    token(block)
    confirm(block)
    block.set_defaults(func=ride.block)
    boarded = branch.add_parser("boarded")
    boarded.add_argument("ride_id")
    token(boarded)
    confirm(boarded)
    boarded.set_defaults(func=ride.boarded)
    carpool = branch.add_parser("carpool").add_subparsers(dest="act", required=True)
    for verb in ["accept", "reject", "dismiss"]:
        leaf = carpool.add_parser(verb)
        leaf.add_argument("offer_id")
        token(leaf)
        confirm(leaf)
        leaf.set_defaults(func=ride.carpool)


def build():
    food, ride, login, geo = hub()
    parser = argparse.ArgumentParser(prog="boogh")
    sub = parser.add_subparsers(dest="cmd", required=True)
    geo_leaf = sub.add_parser("geo")
    geo_leaf.add_argument("query")
    geo_leaf.set_defaults(func=lambda a: login.net.emit(geo.resolve(a.query)))
    food_group(sub, food, login)
    ride_group(sub, ride, login)
    return parser, ride


def main():
    parser, ride = build()
    args = parser.parse_args()
    if getattr(args, "op", None) == "profile" and not getattr(args, "act", None):
        args.func = ride.profile
    if getattr(args, "op", None) == "place" and not getattr(args, "act", None):
        args.func = ride.places
    if not hasattr(args, "token"):
        args.token = None
    try:
        args.func(args)
    except urllib.error.HTTPError as e:
        print(json.dumps({"http": e.code, "body": e.read().decode()[:1000]}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
